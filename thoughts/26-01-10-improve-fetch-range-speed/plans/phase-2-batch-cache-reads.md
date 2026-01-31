---
last_updated: 2026-01-31 08:08
---
# Phase 2: Batch Cache Reads Implementation Plan

## Overview

Replace per-date cache queries with a single batch query to reduce database round-trips when fetching newsletter data for date ranges. Currently, a 3-day sync makes 5 separate Supabase queries; this optimization reduces it to 1 query.

## Current State Analysis

### Cache Query Pattern (from logs)

For a 3-day range (2026-01-16 to 2026-01-18), the current implementation makes:

**Lines 15-16 in log**: `is_date_cached()` checks for past dates
```
GET daily_cache?select=date&date=eq.2026-01-16
GET daily_cache?select=date&date=eq.2026-01-17
```

**Lines 17-19 in log**: `get_daily_payload()` fetches for all dates
```
GET daily_cache?select=payload&date=eq.2026-01-16
GET daily_cache?select=payload&date=eq.2026-01-17
GET daily_cache?select=payload&date=eq.2026-01-18
```

**Total**: 5 queries for 3 dates (scales linearly: 30 days = 62 queries)

### Code Location

The inefficiency is in `tldr_service.py:scrape_newsletters_in_date_range()`:

**Lines 174-188**: Early exit optimization
- Calls `is_date_cached()` for each non-today date
- If all cached, calls `get_daily_payloads_range()` (already optimized!)
- Returns immediately with cached data

**Lines 190-230**: Main processing loop
- Line 194: `get_daily_payload(date_str)` for today
- Line 219: `get_daily_payload(date_str)` for past dates
- Each call is a separate Supabase query

### Existing Batch Function

`storage_service.py:get_daily_payloads_range()` (lines 61-76) already exists:
```python
def get_daily_payloads_range(start_date, end_date):
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache') \
        .select('payload') \
        .gte('date', start_date) \
        .lte('date', end_date) \
        .order('date', desc=True) \
        .execute()

    return [row['payload'] for row in result.data]
```

Returns list of payload objects, each with `date`, `articles`, `issues` fields.

## Desired End State

### Single Batch Query Upfront

```python
# Before the loop - ONE query for entire range
cached_payloads_list = storage_service.get_daily_payloads_range(start_date_text, end_date_text)
cache_map = {p['date']: p for p in cached_payloads_list}

# In the loop - O(1) lookup instead of query
for current_date in dates:
    date_str = util.format_date_for_url(current_date)
    cached_payload = cache_map.get(date_str)  # No database query!
    # ... rest of logic
```

### Query Reduction

| Range | Before | After | Reduction |
|-------|--------|-------|-----------|
| 3 days | 5 queries | 1 query | 5x |
| 7 days | 15 queries | 1 query | 15x |
| 30 days | 62 queries | 1 query | 62x |

### Performance Impact

**Time saved per query**: ~100ms (based on log timestamps)

| Range | Before | After | Savings |
|-------|--------|-------|---------|
| 3 days | ~500ms | ~100ms | ~400ms |
| 7 days | ~1500ms | ~100ms | ~1400ms |
| 30 days | ~6200ms | ~100ms | ~6100ms |

**Note**: While modest for small ranges, this:
1. Scales linearly with range size
2. Reduces database load significantly
3. Simplifies code (no per-date queries)
4. Lays foundation for future optimizations

### Verification

The implementation is correct when:
1. ✅ All dates in range fetched in single query
2. ✅ "Today" special-case logic preserved exactly
3. ✅ Cache-miss behavior identical to current
4. ✅ Early-exit optimization still works
5. ✅ Output matches current implementation exactly

## What We're NOT Doing

- ❌ Changing cache storage schema
- ❌ Modifying cache write logic
- ❌ Optimizing the "today" merge logic
- ❌ Changing payload structure
- ❌ Altering scraping behavior
- ❌ Modifying parallel execution (Phase 1)

## Implementation Approach

Replace per-date cache queries with upfront batch fetch + in-memory map lookup. The batch query is made before the date processing loop, building a dictionary keyed by date for O(1) lookups.

### Key Principles

1. **Preserve "today" semantics**: Today must still merge cached + fresh data
2. **Maintain cache-miss behavior**: Non-cached dates still scrape and cache
3. **Keep early-exit optimization**: All-cached ranges return immediately
4. **Simplify, don't complicate**: Fewer queries = simpler code

## Phase 2 Implementation

### Overview

Replace individual `get_daily_payload()` and `is_date_cached()` calls with a single batch query upfront.

### Changes Required

#### 1. `tldr_service.py:scrape_newsletters_in_date_range()`

**File**: `tldr_service.py`
**Changes**: Replace per-date cache queries with batch fetch + map lookup

**Current structure (lines 156-249)**:
```python
def scrape_newsletters_in_date_range(...):
    # ... setup ...

    # Early exit if all cached (lines 174-188)
    if all(is_date_cached(date) for non-today dates):
        return get_daily_payloads_range(...)  # Already uses batch!

    # Main loop - PER-DATE QUERIES (lines 190-230)
    for current_date in dates:
        if date == today:
            cached_payload = get_daily_payload(date_str)  # QUERY
            # ... today logic ...
        else:
            cached_payload = get_daily_payload(date_str)  # QUERY
            # ... past date logic ...
```

**New structure**:
```python
def scrape_newsletters_in_date_range(...):
    # ... setup ...

    # NEW: Batch fetch all cached payloads upfront (ONE QUERY)
    cached_payloads_list = storage_service.get_daily_payloads_range(
        start_date_text, end_date_text
    )
    cache_map = {payload['date']: payload for payload in cached_payloads_list}

    # Early exit if all cached (SIMPLIFIED - no is_date_cached calls)
    if all(
        util.format_date_for_url(d) != today_str and util.format_date_for_url(d) in cache_map
        for d in dates
    ):
        return {
            "success": True,
            "payloads": cached_payloads_list,  # Already ordered DESC
            "stats": _build_stats_from_payloads(cached_payloads_list, 0),
            "source": "cache",
        }

    # Main loop - O(1) LOOKUPS (no queries)
    for current_date in dates:
        date_str = util.format_date_for_url(current_date)

        if date_str == today_str:
            cached_payload = cache_map.get(date_str)  # O(1) lookup
            # ... today logic (unchanged) ...
        else:
            cached_payload = cache_map.get(date_str)  # O(1) lookup
            # ... past date logic (unchanged) ...
```

**Specific code changes**:

**CHANGE 1**: Add batch fetch after line 172
```python
# After line 172 (after dates_to_write initialization)
# NEW: Batch fetch all cached payloads in one query
cached_payloads_list = storage_service.get_daily_payloads_range(
    start_date_text,
    end_date_text,
)
cache_map = {payload['date']: payload for payload in cached_payloads_list}
```

**CHANGE 2**: Simplify early-exit check (lines 174-188)
```python
# OLD (lines 174-188):
if all(
    util.format_date_for_url(current_date) != today_str
    and storage_service.is_date_cached(util.format_date_for_url(current_date))
    for current_date in dates
):
    cached_payloads = storage_service.get_daily_payloads_range(
        start_date_text,
        end_date_text,
    )
    return {
        "success": True,
        "payloads": cached_payloads,
        "stats": _build_stats_from_payloads(cached_payloads, total_network_fetches),
        "source": "cache",
    }

# NEW:
if all(
    util.format_date_for_url(d) != today_str
    and util.format_date_for_url(d) in cache_map
    for d in dates
):
    return {
        "success": True,
        "payloads": cached_payloads_list,  # Use pre-fetched list
        "stats": _build_stats_from_payloads(cached_payloads_list, 0),
        "source": "cache",
    }
```

**CHANGE 3**: Replace get_daily_payload() for today (line 194)
```python
# OLD (line 194):
cached_payload = storage_service.get_daily_payload(date_str)

# NEW:
cached_payload = cache_map.get(date_str)
```

**CHANGE 4**: Replace get_daily_payload() for past dates (line 219)
```python
# OLD (line 219):
cached_payload = storage_service.get_daily_payload(date_str)

# NEW:
cached_payload = cache_map.get(date_str)
```

### Critical Considerations

#### "Today" Special Case Preservation

The "today" logic (lines 193-217) must remain unchanged:
1. Get cached payload (now from map instead of query)
2. Extract cached URLs
3. Scrape with combined excluded URLs (cached + user-provided)
4. Merge new articles with cached articles
5. Write merged payload to cache

**No behavior changes** - only the cache read method changes.

#### Cache Miss Handling

For past dates (lines 218-230):
- `cache_map.get(date_str)` returns `None` if date not in cache
- This is identical to `get_daily_payload()` returning `None`
- Downstream logic handles `None` correctly (scrapes the date)

**No behavior changes** - `dict.get()` has same semantics as current code.

#### Early Exit Optimization

The early-exit check (lines 174-188) currently:
1. Calls `is_date_cached()` for each non-today date
2. If all return `True`, calls `get_daily_payloads_range()`
3. Returns cached data immediately

**New behavior**:
1. Already have `cache_map` from upfront batch query
2. Check if all non-today dates exist in `cache_map`
3. Return `cached_payloads_list` (already fetched)

**Benefits**:
- Eliminates redundant `is_date_cached()` calls
- Reuses pre-fetched data (no duplicate query)
- Same behavior, fewer queries

### Success Criteria

#### Automated Verification

- [ ] Unit test: `test_batch_cache_read_single_date()` - 1-day range uses cache correctly
- [ ] Unit test: `test_batch_cache_read_multi_date()` - 3-day range uses cache correctly
- [ ] Unit test: `test_batch_cache_read_with_today()` - Today's special-case preserved
- [ ] Unit test: `test_batch_cache_read_cache_miss()` - Missing dates trigger scrape
- [ ] Unit test: `test_batch_cache_read_all_cached()` - Early exit works
- [ ] Integration test: Compare output with Phase 1 for same inputs (must be identical)
- [ ] Log inspection: Verify single `get_daily_payloads_range` query in logs
- [ ] Log inspection: Confirm no `get_daily_payload` or `is_date_cached` queries

#### Manual Verification

- [ ] Fetch 3-day range via UI, verify logs show 1 cache query instead of 5
- [ ] Fetch 7-day range, verify single batch query in logs
- [ ] Fetch range including today, verify "today" logic still works (fresh + cached merge)
- [ ] Fetch range with no cache, verify all dates scraped correctly
- [ ] Fetch fully-cached range, verify early exit with no scraping
- [ ] Compare article counts and content with Phase 1 output (must match exactly)
- [ ] Verify no regressions in rest of project functionality

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to Phase 3.

---

## Testing Strategy

### Unit Tests

Create new test file: `tests/test_tldr_service_cache_batch.py`

**Test 1**: Single date with cache
```python
def test_batch_cache_read_single_date(mocker):
    """Verify single-date range uses batch query."""
    mock_get_range = mocker.patch('storage_service.get_daily_payloads_range')
    mock_get_range.return_value = [
        {'date': '2026-01-15', 'articles': [...], 'issues': [...]}
    ]

    result = tldr_service.scrape_newsletters_in_date_range(
        '2026-01-15', '2026-01-15'
    )

    # Should call batch query once
    mock_get_range.assert_called_once_with('2026-01-15', '2026-01-15')

    # Should NOT call individual queries
    assert not mocker.patch('storage_service.get_daily_payload').called
    assert not mocker.patch('storage_service.is_date_cached').called
```

**Test 2**: Multi-date range with partial cache
```python
def test_batch_cache_read_partial_cache(mocker):
    """Verify mixed cached/uncached dates work correctly."""
    mock_get_range = mocker.patch('storage_service.get_daily_payloads_range')
    mock_get_range.return_value = [
        {'date': '2026-01-15', 'articles': [...], 'issues': [...]}
        # 2026-01-16 and 2026-01-17 NOT in cache
    ]

    mock_scrape = mocker.patch('newsletter_scraper.scrape_date_range')
    mock_scrape.return_value = {'articles': [], 'issues': [], 'stats': {'network_fetches': 0}}

    result = tldr_service.scrape_newsletters_in_date_range(
        '2026-01-15', '2026-01-17'
    )

    # Should call batch query once
    mock_get_range.assert_called_once()

    # Should scrape missing dates (16, 17)
    assert mock_scrape.call_count == 2
```

**Test 3**: All cached with early exit
```python
def test_batch_cache_read_all_cached_early_exit(mocker):
    """Verify early exit when all dates cached."""
    mock_get_range = mocker.patch('storage_service.get_daily_payloads_range')
    mock_get_range.return_value = [
        {'date': '2026-01-17', 'articles': [...], 'issues': [...]},
        {'date': '2026-01-16', 'articles': [...], 'issues': [...]},
        {'date': '2026-01-15', 'articles': [...], 'issues': [...]}
    ]

    mock_scrape = mocker.patch('newsletter_scraper.scrape_date_range')

    result = tldr_service.scrape_newsletters_in_date_range(
        '2026-01-15', '2026-01-17'  # None are today
    )

    # Should call batch query once
    mock_get_range.assert_called_once()

    # Should NOT scrape (early exit)
    mock_scrape.assert_not_called()

    # Should return cached data
    assert result['source'] == 'cache'
    assert len(result['payloads']) == 3
```

**Test 4**: Today's date with cache merge
```python
def test_batch_cache_read_today_merge(mocker, freezegun):
    """Verify today's special-case logic preserved."""
    freezegun.freeze_time('2026-01-18')

    mock_get_range = mocker.patch('storage_service.get_daily_payloads_range')
    mock_get_range.return_value = [
        {'date': '2026-01-18', 'articles': [
            {'url': 'example.com/old', 'title': 'Old Article', ...}
        ], 'issues': [...]}
    ]

    mock_scrape = mocker.patch('newsletter_scraper.scrape_date_range')
    mock_scrape.return_value = {
        'articles': [{'url': 'example.com/new', 'title': 'New Article', ...}],
        'issues': [],
        'stats': {'network_fetches': 1}
    }

    result = tldr_service.scrape_newsletters_in_date_range(
        '2026-01-18', '2026-01-18'
    )

    # Should fetch cache via batch query
    mock_get_range.assert_called_once()

    # Should scrape with excluded cached URLs
    mock_scrape.assert_called_once()
    excluded = mock_scrape.call_args[1]['excluded_urls']
    assert 'example.com/old' in excluded

    # Should merge cached + new articles
    assert result['source'] == 'live'
    payload = result['payloads'][0]
    assert len(payload['articles']) == 2  # old + new
```

### Integration Tests

Add to existing `tests/test_scrape_cache_server.py`:

**Test**: Compare Phase 2 output with Phase 1
```python
def test_phase2_output_matches_phase1(test_client):
    """Verify Phase 2 produces identical output to Phase 1."""
    # Run same query multiple times, compare outputs
    result1 = test_client.post('/api/scrape', json={
        'start_date': '2026-01-15',
        'end_date': '2026-01-17'
    }).json()

    result2 = test_client.post('/api/scrape', json={
        'start_date': '2026-01-15',
        'end_date': '2026-01-17'
    }).json()

    # Payloads should be identical
    assert result1['payloads'] == result2['payloads']
    assert result1['stats']['total_articles'] == result2['stats']['total_articles']
```

### Log Inspection

After implementation, verify logs show:

**Before Phase 2** (5 queries for 3-day range):
```
GET daily_cache?select=date&date=eq.2026-01-16
GET daily_cache?select=date&date=eq.2026-01-17
GET daily_cache?select=payload&date=eq.2026-01-16
GET daily_cache?select=payload&date=eq.2026-01-17
GET daily_cache?select=payload&date=eq.2026-01-18
```

**After Phase 2** (1 query for 3-day range):
```
GET daily_cache?select=payload&date=gte.2026-01-16&date=lte.2026-01-18&order=date.desc
```

### Manual Testing Steps

1. **Clear cache, fetch 3-day range**:
   - Observe logs: Should see 1 batch query, then scraping for uncached dates
   - Verify articles appear correctly in UI

2. **Re-fetch same range (now cached)**:
   - Observe logs: Should see 1 batch query, early exit (no scraping)
   - Verify articles identical to previous fetch

3. **Fetch range including today**:
   - Observe logs: Should see 1 batch query, then scraping for today only
   - Verify "today" section shows fresh + cached articles merged

4. **Fetch 30-day range**:
   - Observe logs: Should see 1 batch query (not 62 queries!)
   - Measure time saved in logs

5. **Compare with Phase 1 output**:
   - Use same date range, same sources
   - Verify article counts match
   - Spot-check article titles and URLs

## Performance Metrics to Capture

Before/after measurements:

| Metric | Before | After | Expected Improvement |
|--------|--------|-------|---------------------|
| 3-day cache queries | 5 | 1 | 5x reduction |
| 7-day cache queries | 15 | 1 | 15x reduction |
| 30-day cache queries | 62 | 1 | 62x reduction |
| 3-day cache time | ~500ms | ~100ms | ~400ms saved |
| 30-day cache time | ~6200ms | ~100ms | ~6100ms saved |

**Note**: These savings are for cache queries only. Total request time also includes scraping (Phase 1 optimized this).

## References

- Research document: `thoughts/26-01-10-improve-fetch-range-speed/research.md` (lines 105-138)
- Phase 1 implementation: `thoughts/26-01-10-improve-fetch-range-speed/phase1-implementation.md`
- Current cache flow: `tldr_service.py` (lines 156-249)
- Batch query function: `storage_service.py` (lines 61-76)
- Log analysis: `.run/26-01-18-9AM-phase-1-iteration-1-serve-py.log` (lines 15-19)
