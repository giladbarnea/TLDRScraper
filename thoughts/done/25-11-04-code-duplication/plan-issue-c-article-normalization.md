---
last_updated: 2025-11-05 06:23, e90f892
---
# Code Duplication Refactoring Plan

## Executive Summary

**Issue C**: Redundant article normalization logic in `newsletter_scraper.py`.

This issue can be resolved with straightforward refactoring that reduces complexity and maintenance burden without over-engineering.


## Issue C: Article Normalization Duplication

### Problem Analysis

**Location**: `/home/user/TLDRScraper/newsletter_scraper.py`

**Duplicated logic in `_build_scrape_response()`** (lines 37-121):
1. Line 47: Normalizes `removed` field for all articles
2. Lines 63-83: Builds article payloads with verbose normalization
3. Line 266 (in `scrape_date_range()`): Another `removed` field normalization

**Specific issues**:
- The `removed` field is normalized in 3 places (lines 47, 70, 266)
- Article payload construction is verbose (lines 63-83)
- Logic is spread out instead of cohesive

### Solution

Extract article normalization into a helper function.

**New function**:
```python
def _normalize_article_payload(article: dict) -> dict:
    """Normalize article dict into API payload format.

    Args:
        article: Raw article dict from adapter

    Returns:
        Normalized article payload dict

    >>> article = {"url": "https://example.com", "title": "Test", "date": "2024-01-01", "category": "Tech", "removed": None}
    >>> result = _normalize_article_payload(article)
    >>> result["removed"]
    False
    """
    payload = {
        "url": article["url"],
        "title": article["title"],
        "date": article["date"],
        "category": article["category"],
        "removed": bool(article.get("removed", False)),
    }

    if article.get("source_id"):
        payload["source_id"] = article["source_id"]
    if article.get("section_title"):
        payload["section_title"] = article["section_title"]
    if article.get("section_emoji"):
        payload["section_emoji"] = article["section_emoji"]
    if article.get("section_order") is not None:
        payload["section_order"] = article["section_order"]
    if article.get("newsletter_type"):
        payload["newsletter_type"] = article["newsletter_type"]

    return payload
```

**Implementation steps**:
1. Add `_normalize_article_payload()` function before `_build_scrape_response()`
2. In `_build_scrape_response()`:
   - Remove line 47 (redundant normalization)
   - Replace lines 63-83 with: `articles_data = [_normalize_article_payload(a) for a in all_articles]`
3. In `scrape_date_range()`:
   - Replace line 266 with call to normalization (or keep as fallback safety check)

**Benefits**:
- Eliminates ~20 lines of redundant code
- Centralizes normalization logic
- Single source of truth for article payload format
- Easier to test with doctest
- More declarative (clear what fields are normalized and how)

**Risks**:
- Minimal. Need to ensure the normalization happens in the right places.
- Keep line 266 as a safety check since it happens after adapter processing.


## Implementation Plan

**Why second**: Isolated to one file, clear boundaries, has doctest for verification.

1. Add `_normalize_article_payload()` function
2. Update `_build_scrape_response()` to use it
3. Review `scrape_date_range()` line 266 (keep as safety check)
4. Run doctests to verify
5. Test with `/api/scrape` endpoint


## Testing Strategy

### Manual Testing Checklist

- [ ] Run `/api/scrape` endpoint
- [ ] Verify all article fields are present in response
- [ ] Check `removed` field is boolean (not null/undefined)
- [ ] Verify section fields are included when present



**Doctest for Issue C**:
```bash
python3 -m doctest newsletter_scraper.py -v
```

**Integration testing**:
```bash
# Test scraping endpoint
curl -X POST http://localhost:5001/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-01", "end_date": "2024-01-01"}'
```

- **Issue C**: If normalization breaks, revert `newsletter_scraper.py`
