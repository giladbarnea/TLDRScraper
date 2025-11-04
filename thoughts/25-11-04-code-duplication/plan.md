---
last-updated: 2025-11-04 21:45, 86afc1c
---
# Code Duplication Refactoring Plan

## Executive Summary

This plan addresses three code duplication issues identified in the TLDRScraper codebase:
- **Issue A**: ~140 lines of duplicated section parsing logic in `tldr_adapter.py`
- **Issue B**: Storage key pattern `newsletters:scrapes:${date}` scattered across 6 locations in 4 files
- **Issue C**: Redundant article normalization logic in `newsletter_scraper.py`

All three issues can be resolved with straightforward refactoring that reduces complexity and maintenance burden without over-engineering.

---

## Issue A: Section Parsing Logic Duplication in TLDRAdapter

### Problem Analysis

**Location**: `/home/user/TLDRScraper/tldr_adapter.py`

**Duplicated code**:
- `parse_articles()` (lines 124-184)
- `extract_issue_metadata()` (lines 256-319)

Both methods contain nearly identical section parsing logic (~60 lines):
- Iterate over markdown lines
- Detect headings with regex pattern `^(#+)\s*(.*)$`
- Handle symbol-only lines (emoji markers)
- Extract emojis from heading text
- Track `pending_section_emoji` state
- Build `NewsletterSection` objects with order, title, emoji

**Key difference**: `parse_articles()` needs to attach section info to articles, while `extract_issue_metadata()` also extracts issue title/subtitle.

### Solution

Extract the common section parsing logic into a private helper method `_parse_sections()`.

**New method signature**:
```python
@staticmethod
def _parse_sections(
    lines: list[str],
    heading_pattern: re.Pattern,
    extract_issue_metadata: bool = False
) -> tuple[list[NewsletterSection], dict]:
    """Parse sections from markdown lines.

    Args:
        lines: List of markdown lines
        heading_pattern: Compiled regex for detecting headings
        extract_issue_metadata: If True, also extract issue title/subtitle

    Returns:
        Tuple of (sections list, metadata dict with optional 'title'/'subtitle')
    """
```

**Implementation approach**:
1. Extract the section parsing loop into `_parse_sections()`
2. Handle both use cases with `extract_issue_metadata` flag
3. Return sections list + metadata dict (title/subtitle when flag is True)
4. Update `parse_articles()` to call `_parse_sections(extract_issue_metadata=False)`
5. Update `extract_issue_metadata()` to call `_parse_sections(extract_issue_metadata=True)`

**Benefits**:
- Eliminates ~60 lines of duplication
- Centralizes section parsing logic
- Bug fixes only need to be applied once
- Easier to test (can test section parsing in isolation)

**Risks**: None. Pure refactoring with no behavior change.

---

## Issue B: localStorage Key Pattern Scattered Everywhere

### Problem Analysis

**Location**: `/home/user/TLDRScraper/client/src/`

The pattern `newsletters:scrapes:${date}` appears in **6 locations across 4 files**:
1. `lib/scraper.js` - lines 52, 126, 167 (3 occurrences)
2. `hooks/useArticleState.js` - line 5 (1 occurrence)
3. `components/ArticleList.jsx` - line 18 (1 occurrence)
4. `components/ResultsDisplay.jsx` - line 45 (1 occurrence)

**Impact**:
- Changing the key format requires updating 6 locations
- Risk of typos causing bugs
- No single source of truth

### Solution

Create a storage key utility that centralizes the pattern.

**File**: Create `/home/user/TLDRScraper/client/src/lib/storageKeys.js`

```javascript
/**
 * Centralized storage key patterns for localStorage
 */

export const STORAGE_KEYS = {
  CACHE_ENABLED: 'cache:enabled'
}

export function getNewsletterScrapeKey(date) {
  return `newsletters:scrapes:${date}`
}
```

**Implementation steps**:
1. Create `client/src/lib/storageKeys.js` with the utility function
2. Update all 6 locations to import and use `getNewsletterScrapeKey(date)`
3. Verify no regressions with manual testing

**Files to update**:
- `client/src/lib/scraper.js` (3 replacements)
- `client/src/hooks/useArticleState.js` (1 replacement)
- `client/src/components/ArticleList.jsx` (1 replacement)
- `client/src/components/ResultsDisplay.jsx` (1 replacement)

**Example replacement**:
```javascript
// Before
const key = `newsletters:scrapes:${date}`

// After
import { getNewsletterScrapeKey } from '../lib/storageKeys'
const key = getNewsletterScrapeKey(date)
```

**Benefits**:
- Single source of truth
- Easier to change format in future
- Reduces risk of typos/inconsistencies
- Better discoverability (all storage keys in one place)

**Risks**: None. Simple string replacement.

---

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

---

## Implementation Order

Recommended sequence (from simplest to most complex):

### Phase 1: Issue B (localStorage keys) - 15 minutes
**Why first**: Simplest change, pure string replacement, no logic changes.

1. Create `client/src/lib/storageKeys.js`
2. Update 6 import statements and 6 call sites
3. Test manually (scrape, check localStorage, verify cache works)

### Phase 2: Issue C (article normalization)
**Why second**: Isolated to one file, clear boundaries, has doctest for verification.

1. Add `_normalize_article_payload()` function
2. Update `_build_scrape_response()` to use it
3. Review `scrape_date_range()` line 266 (keep as safety check)
4. Run doctests to verify
5. Test with `/api/scrape` endpoint

### Phase 3: Issue A (section parsing) - 30 minutes
**Why last**: Most complex, requires careful extraction to preserve behavior.

1. Create `_parse_sections()` helper method
2. Update `parse_articles()` to use it
3. Update `extract_issue_metadata()` to use it
4. Test with TLDR Tech and TLDR AI newsletters
5. Verify section emoji extraction still works correctly

---

## Testing Strategy

### Manual Testing Checklist

**Issue A (Section parsing)**:
- [ ] Scrape TLDR Tech newsletter - verify sections appear correctly
- [ ] Scrape TLDR AI newsletter - verify sections appear correctly
- [ ] Check articles have correct section titles and emojis
- [ ] Check issue metadata has correct sections list

**Issue B (localStorage keys)**:
- [ ] Run scrape with cache enabled
- [ ] Verify localStorage contains keys with correct pattern
- [ ] Check all components can read/write cached data
- [ ] Verify article state updates persist correctly

**Issue C (Article normalization)**:
- [ ] Run `/api/scrape` endpoint
- [ ] Verify all article fields are present in response
- [ ] Check `removed` field is boolean (not null/undefined)
- [ ] Verify section fields are included when present

### Automated Testing

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

---

## Rollback Plan

All changes are pure refactoring with no external API changes:
- **Issue A**: If section parsing breaks, revert `tldr_adapter.py` to previous version
- **Issue B**: If storage breaks, revert all 6 files and `storageKeys.js`
- **Issue C**: If normalization breaks, revert `newsletter_scraper.py`

Git makes rollback trivial since changes are isolated to specific files.

---

## Opportunities

**Add TypeScript types**: Consider adding JSDoc types to `storageKeys.js` for better IDE support  // this is a good idea. do it

---

## Conclusion

This plan addresses all three duplication issues with pragmatic, minimal solutions:
- **Issue A**: Extract ~60 lines into reusable helper
- **Issue B**: Centralize magic string into utility function
- **Issue C**: Extract ~20 lines into normalization function

Total impact:
- **~80 lines removed** from codebase
- **3 new helper functions** added
- **1 new utility file** created
- **Net reduction**: ~70 lines of code
- **Maintenance burden**: Significantly reduced
- **Complexity**: Reduced (fewer places to update)
- **Risk**: Minimal (pure refactoring, no behavior changes)

The refactoring follows project conventions:
- No over-engineering
- Surgical changes only
- Maintains existing architecture
- Reduces complexity
- No band-aid fixes
