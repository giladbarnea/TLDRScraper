---
last_updated: 2026-02-20 13:24, 99f0acd
---
# Analysis: Backend API Routes and Service Layers

## Overview
The backend follows a clean three-layer architecture: `serve.py` (routes/HTTP) → `tldr_app.py` (application orchestration) → `tldr_service.py` (business logic). The app layer is a thin pass-through that delegates to the service layer, which coordinates lower-level modules (storage_service, newsletter_scraper, summarizer). Error handling happens at the route layer with consistent JSON responses.

---

## Complete Route Inventory

### Core Newsletter Endpoints
1. **POST /api/scrape** (`serve.py:42-76`)
   - Scrapes newsletters in date range
   - Body: `start_date`, `end_date`, `sources` (optional), `excluded_urls` (optional)
   - Returns: payloads with articles and issues, plus stats

2. **POST /api/summarize-url** (`serve.py:78-112`)
   - Generates AI summary of URL content
   - Body: `url`, `summarize_effort` (optional)
   - Query: `model` (optional)
   - Returns: summary_markdown, canonical_url, summarize_effort

### Storage/Cache Endpoints
3. **GET /api/storage/setting/:key** (`serve.py:114-131`)
   - Retrieves single setting by key
   - Returns: setting value or 404

4. **POST /api/storage/setting/:key** (`serve.py:132-149`)
   - Upserts setting by key
   - Body: `value`

5. **GET /api/storage/daily/:date** (`serve.py:150-167`)
   - Retrieves cached daily payload for specific date
   - Returns: payload object or 404

6. **POST /api/storage/daily/:date** (`serve.py:168-185`)
   - Updates daily payload (user state changes, no cache timestamp update)
   - Body: `payload`

7. **POST /api/storage/daily-range** (`serve.py:186-205`)
   - Retrieves all cached payloads in date range
   - Body: `start_date`, `end_date`
   - Returns: array of payloads

8. **GET /api/storage/is-cached/:date** (`serve.py:206-220`)
   - Checks if date exists in cache
   - Returns: boolean `is_cached`

### Source/Context Endpoints (Blueprint)
9. **GET /api/source** (`source_routes.py:50-122`)
   - Serves HTML UI for context generation

10. **POST /api/source** (`source_routes.py:125-147`)
    - Generates context XML for specified type
    - Body: `context_type` ('server'|'client'|'docs'|'all')
    - Returns: XML content string

11. **POST /api/source/download** (`source_routes.py:149-179`)
    - Generates and downloads context file
    - Form: `context_types` (JSON array), `only_definitions` (boolean)
    - Returns: text file download

12. **GET /api/source/:context_type** (`source_routes.py:181-204`)
    - Generates and downloads context for specified type
    - Returns: text file download

---

## Layer Flow Pattern: serve.py → tldr_app.py → tldr_service.py

### Entry Point 1: Newsletter Scraping (`POST /api/scrape`)

**serve.py:42-76**
- **Responsibilities:** HTTP request validation, parameter extraction, error handling
- **Input validation:** Checks JSON exists, validates `sources` is array if present
- **Error handling:** Catches ValueError (400), generic Exception (500)
- **Data transformation:** Extracts `start_date`, `end_date`, `sources`, `excluded_urls` from request body
- **Integration point:** Calls `tldr_app.scrape_newsletters()`

**tldr_app.py:10-26**
- **Responsibilities:** Thin delegation layer, no business logic
- **Purpose:** Provides a stable API boundary for route handlers
- **Pass-through:** Directly delegates to `tldr_service.scrape_newsletters_in_date_range()` with same parameters
- **Data transformation:** None (pure delegation)

**tldr_service.py:160-306**
- **Responsibilities:** Core scraping orchestration, caching logic, parallel execution
- **Input validation:**
  - Calls `_parse_date_range()` (27-50) to validate and parse ISO dates
  - Enforces max 31-day range
  - Resolves source_ids to defaults if not provided
- **Cache integration:**
  - Fast path: If all dates cached and fresh, returns cache immediately (204-211)
  - Hybrid path: Merges cached data with fresh scrapes for stale dates
  - Uses `storage_service.get_daily_payloads_range()` for bulk cache fetch (183)
  - Uses `util.should_rescrape()` to determine cache freshness (218)
- **Parallel execution:** ThreadPoolExecutor with configurable workers (238-267)
- **Data transformations:**
  - `_build_payload_from_scrape()` (88-91): Converts raw articles to payload format
  - `_article_to_payload()` (69-85): Adds default state (tldr, read fields)
  - `_merge_payloads()` (94-132): Merges new scrape with cached data, preserving user state
- **Integration points:**
  - `newsletter_scraper.scrape_single_source_for_date()`: Per-source scraping
  - `newsletter_scraper.merge_source_results_for_date()`: Combines multi-source results
  - `storage_service.set_daily_payload_from_scrape()`: Persists to DB (294)

### Entry Point 2: URL Summarization (`POST /api/summarize-url`)

**serve.py:78-112**
- **Responsibilities:** HTTP request handling, parameter extraction, network error handling
- **Input extraction:** Gets `url` and `summarize_effort` from JSON, `model` from query params
- **Error handling:**
  - ValueError → 400
  - requests.RequestException → 502 (network error)
  - Generic Exception → 500
- **Fallback behavior:** Uses `data.get("url", "")` with empty string fallback
- **Integration point:** Calls `tldr_app.summarize_url()`

**tldr_app.py:29-54**
- **Responsibilities:** Response shape formatting, optional field handling
- **Data transformation:**
  - Calls `tldr_service.summarize_url_content()`
  - Builds response dict with `success: True`, `summary_markdown`
  - Conditionally adds `canonical_url` and `summarize_effort` if present
- **Purpose:** Converts service layer output to API contract format

**tldr_service.py:313-344**
- **Responsibilities:** Input validation, URL normalization, AI summarization
- **Input validation:** Raises ValueError if URL is empty/None
- **Data transformations:**
  - `util.canonicalize_url()`: Normalizes URL format (323)
  - `normalize_summarize_effort()`: Validates effort level (324)
- **Integration point:** Calls `summarizer.summarize_url()` (327-331)
- **Error handling:** Catches and re-raises `requests.RequestException` with logging
- **Returns:** Dict with `summary_markdown`, `canonical_url`, `summarize_effort`

---

## Data Flow Patterns

### Scraping Data Flow
1. Request arrives at `serve.py:42` (POST /api/scrape)
2. JSON parsed and validated at `serve.py:46-58`
3. Routed to `tldr_app.scrape_newsletters()` at `serve.py:60-65`
4. Delegated to `tldr_service.scrape_newsletters_in_date_range()` at `tldr_app.py:24-26`
5. Date parsing and validation at `tldr_service.py:164` via `_parse_date_range()`
6. Bulk cache check at `tldr_service.py:183` via `storage_service.get_daily_payloads_range()`
7. Fast path return (204-211) if all cached and fresh
8. Parallel scraping at `tldr_service.py:240-267` via `newsletter_scraper.scrape_single_source_for_date()`
9. Results merged at `tldr_service.py:276` via `merge_source_results_for_date()`
10. Payload transformation at `tldr_service.py:279-287` via `_build_payload_from_scrape()` + `_merge_payloads()`
11. Cache write at `tldr_service.py:294` via `storage_service.set_daily_payload_from_scrape()`
12. Response with stats at `tldr_service.py:301-306`

### Summarization Data Flow
1. Request arrives at `serve.py:78` (POST /api/summarize-url)
2. Extract `url`, `summarize_effort`, `model` at `serve.py:85-90`
3. Routed to `tldr_app.summarize_url()` at `serve.py:87-91`
4. Delegated to `tldr_service.summarize_url_content()` at `tldr_app.py:35-39`
5. URL validation and canonicalization at `tldr_service.py:319-324`
6. AI summarization at `tldr_service.py:327-331` via `summarizer.summarize_url()`
7. Response formatting at `tldr_app.py:41-53` (adds success flag, optional fields)
8. JSON response at `serve.py:93`

### Storage Data Flow (Example: GET setting)
1. Request arrives at `serve.py:114` (GET /api/storage/setting/:key)
2. Routed directly to `storage_service.get_setting(key)` at `serve.py:118`
3. Supabase query at `storage_service.py:10-14`
4. Returns value or None at `storage_service.py:14-15`
5. Response formatting at `serve.py:119-122` (404 if None, else JSON with value)

---

## Error Handling Strategy

### Route Layer (serve.py)
**Pattern:** Consistent try-except blocks with status codes
- **ValueError:** 400 Bad Request (client error)
- **requests.RequestException:** 502 Bad Gateway (network error)
- **Generic Exception:** 500 Internal Server Error

**Response format:** Always `{"success": False, "error": "<message>"}`

**Examples:**
- `serve.py:68-75`: Scrape endpoint catches ValueError (400) and Exception (500)
- `serve.py:95-111`: Summarize endpoint differentiates network errors (502) vs internal (500)
- `serve.py:124-130`: Storage endpoints catch generic Exception (500)

### App Layer (tldr_app.py)
**Pattern:** No error handling - lets exceptions bubble to route layer
- Pure delegation, no try-except blocks
- Service layer exceptions propagate directly to routes

### Service Layer (tldr_service.py)
**Pattern:** Raises ValueError for validation failures, logs but propagates exceptions
- **Input validation:** Raises ValueError with descriptive messages (36, 321)
- **Network errors:** Catches, logs, and re-raises `requests.RequestException` (332-338)
- **Parallel execution errors:** Logs errors but continues processing (251-266)

**Examples:**
- `tldr_service.py:36`: Raises ValueError for missing date fields
- `tldr_service.py:42`: Raises ValueError for invalid ISO date format
- `tldr_service.py:45`: Raises ValueError for start > end
- `tldr_service.py:48`: Raises ValueError for >31 day range
- `tldr_service.py:321`: Raises ValueError for missing URL

### Storage Layer (storage_service.py)
**Pattern:** No error handling - direct Supabase calls
- Database errors bubble up naturally
- Returns None for missing data (not errors)

---

## Naming and Organizational Conventions

### Route Naming
**Pattern:** Verb or noun describing the action
- `scrape_newsletters_in_date_range()` - verb phrase
- `summarize_url_endpoint()` - action with _endpoint suffix
- `get_storage_setting()` / `set_storage_setting()` - CRUD prefix pattern

### App Layer Naming
**Pattern:** Matches route handler names but without _endpoint suffix
- `scrape_newsletters()` - matches route intent
- `summarize_url()` - matches route intent

### Service Layer Naming
**Pattern:** Descriptive verb phrases with domain context
- `scrape_newsletters_in_date_range()` - explicit about scope
- `summarize_url_content()` - explicit about what's being summarized
- Private helpers prefixed with `_`: `_parse_date_range()`, `_build_payload_from_scrape()`, `_merge_payloads()`

### Module Organization
**Pattern:** Layered by responsibility
- **serve.py:** HTTP concerns only (routing, request/response)
- **tldr_app.py:** Application orchestration (thin coordination layer)
- **tldr_service.py:** Business logic (validation, orchestration, transformations)
- **storage_service.py:** Database access (direct Supabase calls)
- **newsletter_scraper.py:** Scraping orchestration (adapter pattern, parallel execution)
- **summarizer.py:** AI summarization (Gemini integration)

---

## App Layer vs Service Layer Separation

### App Layer Responsibilities (`tldr_app.py`)
**Purpose:** Provides stable API boundary between routes and services

**Characteristics:**
- **Thin delegation:** No business logic, just pass-through calls
- **Response shaping:** Formats service output to match API contracts
- **Optional field handling:** Conditionally includes fields in responses (see `summarize_url:41-52`)
- **Stability:** Insulates routes from service layer refactoring

**Example:**
```python
# tldr_app.py:29-54
def summarize_url(...):
    result = tldr_service.summarize_url_content(...)  # Delegate
    payload = {"success": True, "summary_markdown": result["summary_markdown"]}  # Shape response
    if result.get("canonical_url"):  # Handle optional fields
        payload["canonical_url"] = canonical_url
    return payload
```

### Service Layer Responsibilities (`tldr_service.py`)
**Purpose:** Implements core business logic and orchestration

**Characteristics:**
- **Input validation:** Enforces business rules (date ranges, URL format)
- **Caching strategy:** Smart cache-first logic with freshness checks
- **Parallel execution:** Orchestrates concurrent scraping with ThreadPoolExecutor
- **Data transformations:** Normalizes data between layers (raw → payload format)
- **Integration coordination:** Calls lower modules (storage, scraper, summarizer) and combines results
- **Error recovery:** Logs and handles failures without stopping execution

**Example:**
```python
# tldr_service.py:160-306
def scrape_newsletters_in_date_range(...):
    start_date, end_date = _parse_date_range(...)  # Validation
    cache_map = storage_service.get_daily_payloads_range(...)  # Cache check
    if all_cached_and_fresh:  # Caching logic
        return cached_data
    # Parallel scraping orchestration
    with ThreadPoolExecutor(...) as executor:
        # Submit scrape tasks
    # Merge results, transform data, persist cache
    return final_payload
```

---

## Where a New `/api/digest` Endpoint Would Fit

### Recommended Pattern
Based on existing conventions, a new article digest endpoint should follow this structure:

**Route Layer (`serve.py`)**
```python
@app.route("/api/digest", methods=["POST"])
def generate_digest():
    """Generate digest of articles. Body: start_date, end_date, digest_options."""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "error": "No JSON data received"}), 400

        result = tldr_app.generate_digest(
            data.get("start_date"),
            data.get("end_date"),
            digest_options=data.get("digest_options", {}),
        )
        return jsonify(result)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except Exception as error:
        logger.exception("Failed to generate digest: %s", error)
        return jsonify({"success": False, "error": str(error)}), 500
```

**App Layer (`tldr_app.py`)**
```python
def generate_digest(start_date_text, end_date_text, digest_options=None):
    """Generate article digest in date range."""
    result = tldr_service.generate_article_digest(
        start_date_text, end_date_text, digest_options=digest_options or {}
    )
    return {
        "success": True,
        "digest_markdown": result["digest_markdown"],
        "article_count": result["article_count"],
    }
```

**Service Layer (`tldr_service.py`)**
```python
def generate_article_digest(start_date_text, end_date_text, digest_options):
    """Generate article digest with business logic."""
    start_date, end_date = _parse_date_range(start_date_text, end_date_text)

    # Fetch articles from cache/scrape
    payloads = ...

    # Call lower module (e.g., digest_generator.py)
    digest_markdown = digest_generator.create_digest(payloads, digest_options)

    return {
        "digest_markdown": digest_markdown,
        "article_count": len(articles),
    }
```

### Integration Points
1. **Data source:** Reuse `scrape_newsletters_in_date_range()` or directly query `storage_service.get_daily_payloads_range()`
2. **AI layer:** Similar to summarizer.py, create new `digest_generator.py` module
3. **Caching:** Could cache digests in `daily_cache` table or new `digests` table
4. **Error handling:** Follow existing pattern (ValueError → 400, Exception → 500)

### Naming Convention
- Route: `generate_digest()` or `create_article_digest()`
- App: `generate_digest()` (matches route intent)
- Service: `generate_article_digest()` (explicit domain context)
- New module: `digest_generator.py` (follows `summarizer.py` pattern)

---

## Key Files and Code References

### Route Definitions
- `/home/user/TLDRScraper/serve.py:42-220` - All API routes
- `/home/user/TLDRScraper/source_routes.py:50-204` - Source/context blueprint routes

### App Layer
- `/home/user/TLDRScraper/tldr_app.py:10-54` - Application orchestration (2 functions)

### Service Layer
- `/home/user/TLDRScraper/tldr_service.py:27-344` - Business logic (2 public + 6 private functions)

### Lower Modules
- `/home/user/TLDRScraper/storage_service.py:3-115` - Database access (6 functions)
- `/home/user/TLDRScraper/newsletter_scraper.py:14-446` - Scraping orchestration
- `/home/user/TLDRScraper/summarizer.py:1-100+` - AI summarization (truncated view)

### Key Patterns
- **Date validation:** `tldr_service.py:27-50` (`_parse_date_range()`)
- **Cache merge logic:** `tldr_service.py:94-132` (`_merge_payloads()`)
- **Parallel execution:** `tldr_service.py:238-267` (ThreadPoolExecutor pattern)
- **Error handling:** `serve.py:68-75, 95-111, 124-130` (consistent try-except pattern)
- **Response formatting:** `tldr_app.py:41-53` (success flag + optional fields)
