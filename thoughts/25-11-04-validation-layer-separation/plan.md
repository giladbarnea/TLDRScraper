---
last-updated: 2025-11-04 21:02, 02f0e52
---
# Validation Layer Separation Plan

**Status:** Ready for Implementation
**Last Updated:** 2025-11-04
**Issue:** Mixed concerns - route handlers performing business validation

## Executive Summary

The route handler in `serve.py` currently performs business logic validation (checking if `sources` is a list), violating the single responsibility principle. This plan moves validation to the service layer where it belongs, following the existing pattern already established in the codebase.

**Critical Changes Required:**
- 1 validation check moved from route handler to service layer
- Maintains 100% backward compatibility (same HTTP responses)
- Follows existing validation patterns in `tldr_service.py`

**Success Metric:** Route handlers are thin and only handle HTTP concerns. All business validation lives in the service layer.

---

## Current State Analysis

### Validation Locations Audit

| Location | Lines | What's Validated | Layer | Correct? |
|----------|-------|-----------------|-------|----------|
| `serve.py` | 36-37 | JSON data exists | Route | ✅ Yes (HTTP concern) |
| `serve.py` | 40-47 | `sources` parameter type | Route | ❌ **NO** (Business logic) |
| `tldr_service.py` | 17-40 | Date range validation | Service | ✅ Yes |
| `tldr_service.py` | 84-86 | URL presence | Service | ✅ Yes |

### The Problem

**Current Code** (`serve.py` lines 40-47):
```python
sources = data.get("sources")
if sources is not None and not isinstance(sources, list):
    return (
        jsonify(
            {"success": False, "error": "sources must be an array of source IDs"}
        ),
        400,
    )
```

**Why This Is Wrong:**
1. **Violates Single Responsibility Principle** - Route handlers should only handle HTTP concerns (parsing request, formatting response)
2. **Mixes Layers** - Business validation logic is in the HTTP layer
3. **Not Reusable** - If we expose this endpoint through a different interface (CLI, gRPC, etc.), validation logic can't be shared
4. **Hard to Test** - Testing validation requires mocking Flask's request/response objects
5. **Inconsistent** - Other validations are in the service layer (see `_parse_date_range()`, `tldr_url_content()`)

### The Existing Pattern

The codebase already has a clear pattern for this:

**Service Layer Validation** (`tldr_service.py` lines 17-40):
```python
def _parse_date_range(start_date_text: str, end_date_text: str) -> tuple[datetime, datetime]:
    """Parse ISO date strings and enforce range limits."""
    if not start_date_text or not end_date_text:
        raise ValueError("start_date and end_date are required")

    # ... more validation ...

    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")

    if (end_date - start_date).days >= 31:
        raise ValueError("Date range cannot exceed 31 days")

    return start_date, end_date
```

**Route Layer Error Handling** (`serve.py` lines 57-58):
```python
except ValueError as error:
    return jsonify({"success": False, "error": str(error)}), 400
```

This pattern is clean:
- Service layer validates and raises `ValueError` on failure
- Route layer catches `ValueError` and converts to HTTP 400 response
- Validation logic is reusable and testable in isolation

---

## Proposed Architecture

### Layer Responsibilities

```
┌──────────────────────────────────────────────────────┐
│                  serve.py (Routes)                   │
│  Responsibility: HTTP concerns only                  │
│  - Parse request                                     │
│  - Call service layer                                │
│  - Format response                                   │
│  - Convert exceptions to HTTP status codes           │
└──────────────────────┬───────────────────────────────┘
                       │
                       │ Call with validated data
                       ▼
┌──────────────────────────────────────────────────────┐
│              tldr_service.py (Service)               │
│  Responsibility: Business logic & validation         │
│  - Validate inputs                                   │
│  - Enforce business rules                            │
│  - Orchestrate domain operations                     │
│  - Raise ValueError on validation failure            │
└──────────────────────┬───────────────────────────────┘
                       │
                       │ Delegate to domain
                       ▼
┌──────────────────────────────────────────────────────┐
│          newsletter_scraper.py (Domain)              │
│  Responsibility: Core business operations            │
│  - Scrape newsletters                                │
│  - Parse articles                                    │
│  - Deduplicate                                       │
└──────────────────────────────────────────────────────┘
```

---

## Detailed Implementation Plan

### Step 1: Move Validation to Service Layer

**File:** `tldr_service.py`

**Add validation helper** (after `_parse_date_range`, around line 42):

```python
def _validate_source_ids(source_ids: list[str] | None) -> None:
    """Validate source_ids parameter.

    Args:
        source_ids: Optional list of source IDs to scrape

    Raises:
        ValueError: If source_ids is not None and not a list

    >>> _validate_source_ids(None)
    >>> _validate_source_ids(["tldr_tech"])
    >>> _validate_source_ids("invalid")  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: sources must be an array of source IDs
    """
    if source_ids is not None and not isinstance(source_ids, list):
        raise ValueError("sources must be an array of source IDs")
```

**Update** `scrape_newsletters_in_date_range()` (line 43):

```python
def scrape_newsletters_in_date_range(
    start_date_text: str, end_date_text: str, source_ids: list[str] | None = None, excluded_urls: list[str] | None = None
) -> dict:
    """Scrape newsletters in date range.

    Args:
        start_date_text: Start date in ISO format
        end_date_text: End date in ISO format
        source_ids: Optional list of source IDs to scrape. Defaults to all configured sources.
        excluded_urls: List of canonical URLs to exclude from results

    Returns:
        Response dictionary with articles and issues
    """
    # Validate inputs
    start_date, end_date = _parse_date_range(start_date_text, end_date_text)
    _validate_source_ids(source_ids)  # NEW LINE

    sources_str = ", ".join(source_ids) if source_ids else "all"
    excluded_count = len(excluded_urls) if excluded_urls else 0
    # ... rest of function unchanged
```

### Step 2: Simplify Route Handler

**File:** `serve.py`

**Remove validation logic** (lines 40-47):

**BEFORE:**
```python
@app.route("/api/scrape", methods=["POST"])
def scrape_newsletters_in_date_range():
    """Backend proxy to scrape newsletters. Expects start_date, end_date, excluded_urls, and optionally sources in the request body."""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "error": "No JSON data received"}), 400

        # Extract sources parameter (optional)
        sources = data.get("sources")
        if sources is not None and not isinstance(sources, list):
            return (
                jsonify(
                    {"success": False, "error": "sources must be an array of source IDs"}
                ),
                400,
            )

        result = tldr_app.scrape_newsletters(
            data.get("start_date"),
            data.get("end_date"),
            source_ids=sources,
            excluded_urls=data.get("excluded_urls", []),
        )
        return jsonify(result)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
```

**AFTER:**
```python
@app.route("/api/scrape", methods=["POST"])
def scrape_newsletters_in_date_range():
    """Backend proxy to scrape newsletters. Expects start_date, end_date, excluded_urls, and optionally sources in the request body."""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "error": "No JSON data received"}), 400

        result = tldr_app.scrape_newsletters(
            data.get("start_date"),
            data.get("end_date"),
            source_ids=data.get("sources"),
            excluded_urls=data.get("excluded_urls", []),
        )
        return jsonify(result)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
```

**Changes:**
- ✅ Removed lines 40-47 (validation logic)
- ✅ Directly pass `data.get("sources")` to service layer
- ✅ Existing `ValueError` handler catches validation failures from service layer
- ✅ Same HTTP 400 response with same error message (backward compatible)

---

## Backward Compatibility

### API Contract (Unchanged)

**Request:**
```json
POST /api/scrape
{
    "start_date": "2024-01-01",
    "end_date": "2024-01-03",
    "sources": ["tldr_tech", "tldr_ai"],  // Optional
    "excluded_urls": []
}
```

**Response (success):**
```json
{
    "success": true,
    "articles": [...],
    "issues": [...]
}
```

**Response (validation error):**
```json
{
    "success": false,
    "error": "sources must be an array of source IDs"
}
```
HTTP Status: `400 Bad Request`

### Validation Behavior (Identical)

| Input | Before | After | Status |
|-------|--------|-------|--------|
| `sources: null` | ✅ Pass | ✅ Pass | Unchanged |
| `sources: ["tldr_tech"]` | ✅ Pass | ✅ Pass | Unchanged |
| `sources: "tldr_tech"` | ❌ 400 error | ❌ 400 error | Unchanged |
| `sources: 123` | ❌ 400 error | ❌ 400 error | Unchanged |

The only difference is **where** the validation happens (route vs service). The **behavior** is identical.

---

## Testing Strategy

### Manual Testing

**Before implementation:**
```bash
# Start server
source ./setup.sh
start_server_and_watchdog

# Test valid request
curl -X POST http://localhost:5001/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2024-01-01","end_date":"2024-01-01","sources":["tldr_tech"]}'

# Test invalid request (sources as string)
curl -X POST http://localhost:5001/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2024-01-01","end_date":"2024-01-01","sources":"tldr_tech"}'

# Expected: {"success":false,"error":"sources must be an array of source IDs"}
```

**After implementation:**
```bash
# Run same tests again - behavior should be identical
```

### Unit Testing (Recommended Future Addition)

**Service Layer Test** (can now be tested in isolation):
```python
import pytest
from tldr_service import _validate_source_ids

def test_validate_source_ids_none():
    _validate_source_ids(None)  # Should not raise

def test_validate_source_ids_valid_list():
    _validate_source_ids(["tldr_tech", "tldr_ai"])  # Should not raise

def test_validate_source_ids_invalid_string():
    with pytest.raises(ValueError, match="sources must be an array"):
        _validate_source_ids("tldr_tech")

def test_validate_source_ids_invalid_number():
    with pytest.raises(ValueError, match="sources must be an array"):
        _validate_source_ids(123)
```

**Note:** Service layer tests don't need Flask mocking - they're pure Python functions.

---

## Why This Solution Is Good

### 1. Follows Existing Patterns

The solution exactly mirrors the existing `_parse_date_range()` pattern:
- Private helper function `_validate_source_ids()`
- Raises `ValueError` on failure
- Called at the start of `scrape_newsletters_in_date_range()`
- Route handler catches `ValueError` and returns 400

### 2. Pragmatic

- Minimal changes (10 lines added, 8 lines removed)
- No new dependencies
- No breaking changes
- No complex refactoring

### 3. Improves Testability

**Before:**
```python
# Hard to test - needs Flask app context
def test_sources_validation():
    with app.test_client() as client:
        response = client.post('/api/scrape', json={...})
        # Test involves HTTP layer
```

**After:**
```python
# Easy to test - pure function
def test_sources_validation():
    _validate_source_ids("invalid")
    # Just test the validation logic
```

### 4. Enables Reusability

If we later expose the same functionality through a different interface:
```python
# CLI interface
def cli_scrape(args):
    result = tldr_service.scrape_newsletters_in_date_range(
        args.start_date,
        args.end_date,
        source_ids=args.sources  # Same validation applies
    )
```

### 5. Better Error Context

Service layer can provide richer error messages:
```python
# Future enhancement (optional)
if source_ids is not None:
    if not isinstance(source_ids, list):
        raise ValueError("sources must be an array of source IDs")

    # Can add more validation here
    from newsletter_config import NEWSLETTER_CONFIGS
    invalid = [s for s in source_ids if s not in NEWSLETTER_CONFIGS]
    if invalid:
        raise ValueError(f"Unknown source IDs: {', '.join(invalid)}")
```

---

## Implementation Checklist

- [ ] Add `_validate_source_ids()` helper to `tldr_service.py`
- [ ] Call `_validate_source_ids()` in `scrape_newsletters_in_date_range()`
- [ ] Remove validation logic from `serve.py` (lines 40-47)
- [ ] Update `serve.py` to pass `data.get("sources")` directly
- [ ] Test with valid `sources` list
- [ ] Test with `sources: null`
- [ ] Test with invalid `sources` (string)
- [ ] Test with invalid `sources` (number)
- [ ] Verify HTTP 400 response format is unchanged
- [ ] Verify error message is unchanged

---

## Future Enhancements (Out of Scope)

These are **not** part of this refactor but could be considered later:

1. **Validate source IDs exist in config:**
   ```python
   invalid = [s for s in source_ids if s not in NEWSLETTER_CONFIGS]
   if invalid:
       raise ValueError(f"Unknown source IDs: {', '.join(invalid)}")
   ```

2. **Validate excluded_urls:**
   ```python
   if excluded_urls is not None and not isinstance(excluded_urls, list):
       raise ValueError("excluded_urls must be an array")
   ```

3. **Add unit tests for validation functions**

4. **Consider validation library** (e.g., Pydantic) if validation gets more complex

---

## Conclusion

This refactor is surgical and pragmatic:
- Moves 1 validation check to the correct layer
- Follows existing codebase patterns
- Maintains 100% backward compatibility
- Improves testability and maintainability
- Requires minimal code changes

The result is a cleaner separation of concerns where route handlers are thin and only handle HTTP details, while the service layer owns all business logic and validation.
