---
last_updated: 2026-01-22 11:17, c38f4ba
---
# Phase 2: Batch Cache Reads Implementation Plan

## Overview

Optimize `tldr_service.scrape_newsletters_in_date_range` to fetch all cached payloads in a single Supabase query upfront, instead of N per-date queries.

## Current State Analysis

The "slow path" at `tldr_service.py:190-230` makes individual `storage_service.get_daily_payload(date_str)` calls:
- Line 194: `cached_payload = storage_service.get_daily_payload(date_str)` (for today)
- Line 219: `cached_payload = storage_service.get_daily_payload(date_str)` (for past dates)

For a 3-day range, this results in 3 sequential Supabase round-trips.

The batch function `storage_service.get_daily_payloads_range(start_date, end_date)` already exists (`storage_service.py:61-76`) but is only used in the "fast path" (`tldr_service.py:179-182`) which is never taken when today is in the range.

## Desired End State

All cache reads happen in a single upfront `get_daily_payloads_range` call, with results indexed in a local dict for O(1) lookups during the date loop.

### Verification:
- Logging shows single cache fetch at start
- Response payloads unchanged
- Performance improvement measurable on multi-day syncs

## What We're NOT Doing

- Changing the "today" special-case behavior (still union cached + live scrape)
- Modifying the fast-path logic (lines 174-188)
- Touching scrape execution or storage writes

## Implementation Approach

Fetch all cached payloads once before the date loop, index by date string, then use dict lookups instead of per-date Supabase calls.

## Phase 1: Batch Cache Reads

### Overview
Replace N per-date `get_daily_payload` calls with 1 upfront `get_daily_payloads_range` call.

### Changes Required:

#### 1. Add upfront batch fetch before the date loop
**File**: `tldr_service.py`
**Location**: After line 172 (before line 174's fast-path check)

```python
    # Fetch all cached payloads upfront in one query
    all_cached_payloads = storage_service.get_daily_payloads_range(start_date_text, end_date_text)
    cache_map: dict[str, dict] = {payload["date"]: payload for payload in all_cached_payloads}
```

#### 2. Replace per-date cache calls with dict lookups
**File**: `tldr_service.py`

**Change at line 194** (today branch):
```python
# Before:
cached_payload = storage_service.get_daily_payload(date_str)

# After:
cached_payload = cache_map.get(date_str)
```

**Change at line 219** (past dates branch):
```python
# Before:
cached_payload = storage_service.get_daily_payload(date_str)

# After:
cached_payload = cache_map.get(date_str)
```

#### 3. Simplify the fast-path check
**File**: `tldr_service.py`
**Location**: Lines 174-188

The fast-path can now use `cache_map` for the all-cached check instead of calling `is_date_cached` per date:

```python
# Before:
if all(
    util.format_date_for_url(current_date) != today_str
    and storage_service.is_date_cached(util.format_date_for_url(current_date))
    for current_date in dates
):
    cached_payloads = storage_service.get_daily_payloads_range(...)

# After:
all_dates_cached_and_not_today = all(
    util.format_date_for_url(d) != today_str and util.format_date_for_url(d) in cache_map
    for d in dates
)
if all_dates_cached_and_not_today:
    return {
        "success": True,
        "payloads": [cache_map[util.format_date_for_url(d)] for d in reversed(dates)],
        "stats": _build_stats_from_payloads(list(cache_map.values()), 0),
        "source": "cache",
    }
```

### Success Criteria:

#### Automated Verification:
- [ ] `uv run python3 -m doctest tldr_service.py` passes
- [ ] Server starts without errors: `source setup.sh && start_server_and_watchdog`
- [ ] `curl -X POST http://localhost:5001/api/scrape -H "Content-Type: application/json" -d '{"start_date":"2026-01-20","end_date":"2026-01-22"}'` returns valid response

#### Manual Verification:
- [ ] App loads and displays articles correctly
- [ ] Multi-day sync returns same data as before (compare payloads)
- [ ] Server logs show single cache fetch instead of N fetches

**Implementation Note**: After completing this phase, pause for manual confirmation that behavior is unchanged.

---

## Testing Strategy

### Manual Testing Steps:
1. Start server, open app, observe load behavior
2. Check server logs for cache query pattern (should see one batch fetch)
3. Compare article counts before/after to ensure no data loss
4. Test with various date ranges (1 day, 3 days, 7 days)

## References

- Research document: `thoughts/26-01-10-improve-fetch-range-speed/research.md` (lines 105-138)
- Current implementation: `tldr_service.py:156-249`
- Batch query function: `storage_service.py:61-76`
