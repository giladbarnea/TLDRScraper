---
created: 2025-12-16
revised: 2025-12-19
last_updated: 2025-12-19 00:27
---
# Fix Cache-Scrape Edge Case for Today (Revised Plan)

## Problem

When a user scrapes today's date, the results are cached. If sources publish new articles later that day and the user scrapes again, the new articles are not detected. The client-side cache check prevents the server from being called at all.

## Current Behavior

1. Client checks if date is cached via `isRangeCached()` (scraper.js:49-62)
2. If cached, returns stored data immediately — server never called
3. Cache check only verifies row existence, not freshness
4. New intra-day articles are invisible to the user

## Why the Original Plan Was Flawed

The original plan proposed that the server return "only new articles" for today. This approach has critical defects:

1. **Data Loss**: `mergeWithCache()` (scraper.js:132-165) iterates over incoming articles and overlays state from cached articles. It does NOT retain cached articles missing from the incoming payload. If the server returns only new articles, all previously cached articles for today are deleted, along with their `read`/`removed`/`tldr` state.

2. **Incorrect Stats**: Stats are calculated based on `all_articles` collected during scrape. If `excluded_urls` prevents existing articles from being added, stats reflect only the delta (e.g., "1 article found") rather than the day's total.

3. **Inefficient Re-scraping**: Returning `false` from `isRangeCached` for any range containing today forces re-scraping the entire range, including already-cached past days.

## Invariants

- If a URL is already cached, its content is not re-fetched
- If a TLDR is already generated, it is not regenerated
- User state (read, removed, tldrHidden) is never lost on re-scrape
- Past dates (not today) retain current cache-first behavior
- Client remains unaware of URL-level caching — server handles it internally
- Stats always reflect the full dataset for the requested range

## Revised Approach: Server-Side Union

The server becomes responsible for merging cached and new data, returning a complete payload. The client continues to trust the server's response.

---

## Implementation

### Phase 1: Server-Side Smart Scrape Orchestration ✓

#### File: `tldr_service.py`

**Location**: `scrape_newsletters_in_date_range()` (lines 45-72)

**Current behavior**: Calls `scrape_date_range()` for the entire range without checking storage.

**New behavior**:
1. Parse the date range
2. Determine which dates are "today" vs "past"
3. For **past dates**: Load cached payloads from `storage_service.get_daily_payload()`; skip scraping if cached
4. For **today**: Apply Server-Side Union logic (see below)
5. Combine all results and return

**Key changes**:
- Import `storage_service` and `datetime.date`
- Add helper to detect if a date is "today" using date-only comparison
- Iterate dates individually, applying different logic per date type
- Union cached + scraped articles for today
- Recalculate unified stats across all dates

```python
# Pseudocode for revised flow:
import storage_service
from datetime import date as date_type

def scrape_newsletters_in_date_range(start_date_text, end_date_text, source_ids=None, excluded_urls=None):
    start_date, end_date = _parse_date_range(start_date_text, end_date_text)
    dates = util.get_date_range(start_date, end_date)
    today_str = date_type.today().isoformat()

    all_articles = []
    all_issues = []
    url_set = set()

    for current_date in dates:
        date_str = util.format_date_for_url(current_date)

        if date_str == today_str:
            # TODAY: Server-Side Union
            cached_payload = storage_service.get_daily_payload(date_str)
            cached_urls = set()
            cached_articles = []
            cached_issues = []

            if cached_payload:
                cached_articles = cached_payload.get('articles', [])
                cached_issues = cached_payload.get('issues', [])
                cached_urls = {a['url'] for a in cached_articles}

            # Scrape today with cached URLs excluded
            combined_excluded = list(set(excluded_urls or []) | cached_urls)
            result = scrape_date_range(current_date, current_date, source_ids, combined_excluded)

            # Union: cached + newly scraped
            new_articles = result.get('articles', [])
            new_issues = result.get('issues', [])

            # Merge articles (cached first, then new)
            for article in cached_articles:
                url = article.get('url') or article.get('canonical_url')
                if url and url not in url_set:
                    url_set.add(url)
                    all_articles.append(article)
            for article in new_articles:
                url = article.get('url')
                if url and url not in url_set:
                    url_set.add(url)
                    all_articles.append(article)

            # Merge issues (by key: date+source_id+category)
            issue_keys = {(i.get('date'), i.get('source_id'), i.get('category')) for i in all_issues}
            for issue in cached_issues + new_issues:
                key = (issue.get('date'), issue.get('source_id'), issue.get('category'))
                if key not in issue_keys:
                    issue_keys.add(key)
                    all_issues.append(issue)
        else:
            # PAST DATE: Cache-first
            cached_payload = storage_service.get_daily_payload(date_str)
            if cached_payload:
                for article in cached_payload.get('articles', []):
                    url = article.get('url') or article.get('canonical_url')
                    if url and url not in url_set:
                        url_set.add(url)
                        all_articles.append(article)
                for issue in cached_payload.get('issues', []):
                    all_issues.append(issue)
            else:
                # Not cached, must scrape
                result = scrape_date_range(current_date, current_date, source_ids, excluded_urls)
                for article in result.get('articles', []):
                    url = article.get('url')
                    if url and url not in url_set:
                        url_set.add(url)
                        all_articles.append(article)
                for issue in result.get('issues', []):
                    all_issues.append(issue)

    # Build unified response with recalculated stats
    # ... (use existing _build_scrape_response pattern)
```

**Design notes**:
- Use `datetime.date.today().isoformat()` for "today" detection (server timezone)
- The existing `excluded_urls` parameter threads through to adapters unchanged
- Canonicalize URLs when building `cached_urls` set using `util.canonicalize_url()`
- Stats are computed from the final unified `all_articles` list

---

### Phase 2: Client-Side Cache Bypass for Today ✓

#### File: `client/src/lib/scraper.js`

**Location**: `isRangeCached()` function (lines 49-62)

**Current behavior**: Returns `true` if all dates in range are cached, regardless of whether "today" is included.

**New behavior**: Return `false` if any date in the range is "today" (even if cached), forcing a server call. Use date-only comparison to avoid timezone edge cases.

**Change**:
```javascript
async function isRangeCached(startDate, endDate, cacheEnabled) {
  if (!cacheEnabled) return false

  const dates = computeDateRange(startDate, endDate)

  // Bypass cache if "today" is in range (server will handle union)
  const todayStr = new Date().toISOString().split('T')[0]
  if (dates.includes(todayStr)) {
    return false
  }

  for (const date of dates) {
    const isCached = await storageApi.isDateCached(date)
    if (!isCached) {
      return false
    }
  }

  return true
}
```

**Rationale**:
- Server now handles the union logic, so the client just needs to ensure the server is called for today
- No changes to `mergeWithCache()` needed — since the server returns the full payload, the existing merge logic correctly preserves user state for matching URLs and adds new articles

---

### Phase 3: Normalization Safety

#### Timezone Considerations

- **Server**: Use `datetime.date.today().isoformat()` — yields `YYYY-MM-DD` in server's local timezone
- **Client**: Use `new Date().toISOString().split('T')[0]` — yields `YYYY-MM-DD` in UTC

**Potential edge case**: If the server is in a different timezone than the client, "today" may differ. For this project (single-user context), this is acceptable. For production, consider:
1. Having the client send its local date as a parameter
2. Or using UTC consistently on both sides

For now, no additional changes needed — the server's "today" is authoritative.

---

## Files Changed Summary

| File | Change |
|------|--------|
| `tldr_service.py` | Rewrite `scrape_newsletters_in_date_range()` to iterate dates individually, load cached payloads for past dates, apply union logic for today |
| `client/src/lib/scraper.js` | Add "today" check in `isRangeCached()` to force server call |

## What We're NOT Changing

- `newsletter_scraper.py`: No changes — `scrape_date_range()` continues to work for single-date scrapes
- `storage_service.py`: No changes — existing `get_daily_payload()` is sufficient
- `mergeWithCache()` in scraper.js: No changes — server returns full payload, existing merge works correctly
- TLDR generation flow: Unchanged
- Past-date caching behavior when today is NOT in range: Unchanged

---

## Verification

### Test 1: Fresh Scrape of Today
1. Clear today's cache (or use a fresh date)
2. Scrape today → articles cached
3. Note article count

### Test 2: Re-scrape Today After New Content
1. After initial scrape, manually remove one URL from cache OR wait for source to publish new content
2. Scrape today again
3. **Expected**: New articles appear, existing articles retain their state (read, removed, tldr)
4. **Expected**: Stats reflect total count (cached + new)

### Test 3: Mixed Range (Yesterday + Today)
1. Ensure yesterday is cached
2. Scrape [yesterday, today]
3. **Expected**: Yesterday loaded from cache (no network fetch), today scraped and unioned
4. **Expected**: Stats reflect combined totals

### Test 4: Past Date Only
1. Scrape a past date that's already cached
2. **Expected**: Cache-first behavior unchanged — no server call if fully cached

### Test 5: User State Preservation
1. Scrape today, mark some articles as read/removed, generate a TLDR
2. Wait or mock new content
3. Scrape today again
4. **Expected**: Read/removed/tldr state preserved on existing articles, new articles added

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Timezone mismatch between client and server | Acceptable for single-user; can add client-sent date param if needed |
| Performance regression from per-date iteration | Minimal — storage reads are fast; only "today" requires network |
| Cached payload format mismatch | Storage returns same format as scrape response; normalize if needed |
