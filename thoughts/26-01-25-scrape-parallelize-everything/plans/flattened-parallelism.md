---
last_updated: 2026-01-25 15:37
---
# Flattened Single-Level Parallelism Implementation Plan

## Overview

Replace the current sequential date iteration with a **single-level parallel architecture** that processes (date, source) work items concurrently. This provides date-level parallelism while maintaining a single global concurrency cap, avoiding the complexity of nested thread pools.

## Current State Analysis

### Architecture

```
tldr_service.scrape_newsletters_in_date_range()     ← Sequential date loop
  └─ for date in dates:
       └─ newsletter_scraper.scrape_date_range(date, date, ...)
            └─ ThreadPoolExecutor                   ← Parallel source loop
                 └─ adapter.scrape_date()
```

**Key files:**
- `tldr_service.py:156-254` - Date orchestration, cache logic, payload merging
- `newsletter_scraper.py:503-595` - Per-date source coordination with ThreadPoolExecutor
- `newsletter_scraper.py:390-452` - `_scrape_sources_for_date_parallel()` worker implementation
- `newsletter_scraper.py:255-311` - `_collect_newsletters_for_date_from_source_worker()` thread-safe worker

### Key Discoveries

1. `scrape_date_range()` is always called with `start == end` (single date) from `tldr_service`
2. Per-source parallelism already exists and is well-tested
3. Cache reads are batched upfront; writes happen per-date after scraping
4. Deterministic ordering is preserved by merging results in original source order
5. `excluded_urls` flow: cached URLs are excluded to prevent refetching known articles

## Desired End State

A single `ThreadPoolExecutor` in `tldr_service.py` processes `(date, source)` work items with:
- Global concurrency cap (e.g., `MAX_PARALLEL_SCRAPES=20`)
- Same deterministic ordering guarantees
- Same cache semantics (freshness check, URL exclusion, payload merging)
- Same or better wall-clock performance for multi-day scrapes

**Verification:**
- 7-day scrape with cold cache completes faster than sequential baseline
- Output payloads are byte-identical to sequential mode for same inputs
- No rate limiting errors from external sources with conservative worker count

## What We're NOT Doing

- Changing the adapter layer or `scrape_date()` interface
- Modifying cache storage schema or freshness logic
- Adding new env vars beyond a single `MAX_PARALLEL_SCRAPES`
- Removing backward compatibility (sequential mode remains available)

## Implementation Approach

1. **Extract** a single (date, source) scrape function from the existing worker
2. **Flatten** the work queue to `[(date, source, excluded_urls), ...]` tuples
3. **Parallelize** with a single `ThreadPoolExecutor` and global cap
4. **Collect** results grouped by date, then merge deterministically
5. **Write** to storage sequentially from the main thread (unchanged)

---

## Phase 1: Extract Single-Item Scrape Function

### Overview
Create a pure function that scrapes one (date, source) pair, returning articles and metadata. This becomes the parallelizable unit of work.

### Changes Required

#### 1. New worker function in `newsletter_scraper.py`

**File**: `newsletter_scraper.py`

**Changes**: Add a new function `scrape_single_source_for_date()` that:
- Takes `(date, source_id, excluded_urls)` as inputs
- Returns `(date_str, source_id, articles, issues, network_count, error)`
- Is completely stateless and thread-safe
- Reuses existing adapter instantiation and `scrape_date()` logic

```python
def scrape_single_source_for_date(date, source_id, excluded_urls):
    """Scrape a single source for a single date. Thread-safe, stateless."""
    # Returns: (date_str, source_id, articles, issues, network_count, error)
```

This function should be extracted from the existing `_collect_newsletters_for_date_from_source_worker()` with minimal changes.

### Success Criteria

#### Automated Verification
- [ ] `uv run python3 -c "from newsletter_scraper import scrape_single_source_for_date; print('import ok')"`
- [ ] Function signature matches spec (6-tuple return)

#### Manual Verification
- [ ] Quick sanity call with a single date/source returns expected structure

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding to Phase 2.

---

## Phase 2: Add Flattened Parallelism to Service Layer

### Overview
Replace sequential date iteration in `tldr_service.py` with a single `ThreadPoolExecutor` that processes (date, source) work items.

### Changes Required

#### 1. New parallel orchestration in `tldr_service.py`

**File**: `tldr_service.py`

**Changes**: Modify `scrape_newsletters_in_date_range()` to:

1. Build a flat list of work items after cache check:
```python
work_items = []
for date in dates:
    if should_rescrape(date, cached_at_map.get(date_str)):
        cached_urls = extract_cached_urls(cache_map.get(date_str))
        for source_id in source_ids:
            work_items.append((date, source_id, cached_urls))
```

2. Process with single ThreadPoolExecutor:
```python
from newsletter_scraper import scrape_single_source_for_date

max_workers = int(util.resolve_env_var("MAX_PARALLEL_SCRAPES", default="20"))

results_by_date = defaultdict(list)
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = {
        executor.submit(scrape_single_source_for_date, d, s, excl): (d, s)
        for d, s, excl in work_items
    }
    for future in as_completed(futures):
        date_str, source_id, articles, issues, net_count, error = future.result()
        results_by_date[date_str].append((source_id, articles, issues, net_count, error))
```

3. Merge results deterministically (by original source order):
```python
for date_str in dates_needing_scrape:
    source_results = results_by_date[date_str]
    # Sort by original source_ids order for determinism
    ordered_results = sorted(source_results, key=lambda r: source_ids.index(r[0]))
    merged_articles = []
    for source_id, articles, issues, net_count, error in ordered_results:
        merged_articles.extend(articles)
    # Build payload and merge with cache
    new_payload = _build_payload_from_scrape(merged_articles, ...)
    payloads_by_date[date_str] = _merge_payloads(new_payload, cache_map.get(date_str))
```

4. Write to storage (unchanged, sequential in main thread)

#### 2. New env var

**File**: Environment / deployment config

**Changes**: Add `MAX_PARALLEL_SCRAPES` env var (default: 20)

### Success Criteria

#### Automated Verification
- [ ] Server starts without errors: `source setup.sh && start_server_and_watchdog`
- [ ] `/api/scrape` returns valid response for single day
- [ ] `/api/scrape?start=2026-01-20&end=2026-01-25` returns valid response for date range

#### Manual Verification
- [ ] Compare 7-day scrape output between old (sequential) and new (parallel) modes - payloads should match
- [ ] Observe logs showing parallel execution (interleaved source fetches across dates)
- [ ] Verify no rate limiting errors from external sources

**Implementation Note**: After completing this phase, pause for manual verification of output equivalence before proceeding.

---

## Phase 3: Remove Redundant Per-Date Parallelism

### Overview
Since parallelism now lives in `tldr_service`, the per-source ThreadPoolExecutor in `newsletter_scraper.py` is redundant. Simplify by removing it and making `scrape_date_range()` a thin wrapper or deprecating it.

### Changes Required

#### 1. Simplify or deprecate `scrape_date_range()`

**File**: `newsletter_scraper.py`

**Options**:

**Option A (Preserve interface)**: Keep `scrape_date_range()` but make it call `scrape_single_source_for_date()` sequentially. This maintains backward compatibility if anything else uses it.

**Option B (Deprecate)**: If only `tldr_service` calls `scrape_date_range()`, and we've moved parallelism there, remove the function and have `tldr_service` call `scrape_single_source_for_date()` directly.

**Recommended**: Option A initially for safety, then Option B after confirming no other callers.

#### 2. Remove `ENABLE_PARALLEL_SCRAPING` and `SCRAPER_MAX_WORKERS` env vars

**File**: Environment / deployment config, `newsletter_scraper.py`

**Changes**: These become obsolete. Remove references after confirming the new approach works.

### Success Criteria

#### Automated Verification
- [ ] No references to old env vars in codebase: `grep -r "ENABLE_PARALLEL_SCRAPING\|SCRAPER_MAX_WORKERS" --include="*.py"`
- [ ] All existing tests pass

#### Manual Verification
- [ ] End-to-end scrape still works as expected
- [ ] Performance matches or exceeds Phase 2

---

## Phase 4: Benchmark and Tune

### Overview
Measure actual performance gains and tune `MAX_PARALLEL_SCRAPES` for optimal throughput without triggering rate limits.

### Changes Required

#### 1. Add timing instrumentation

**File**: `tldr_service.py`

**Changes**: Log wall-clock time for the parallel scrape section:
```python
import time
start = time.perf_counter()
# ... parallel scrape ...
elapsed = time.perf_counter() - start
util.log(f"Parallel scrape completed: {len(work_items)} items in {elapsed:.2f}s")
```

#### 2. Benchmark different worker counts

Test with `MAX_PARALLEL_SCRAPES` values: 10, 20, 30, 40

Record:
- Wall-clock time for 7-day cold cache scrape
- Any rate limiting errors or failures
- CPU/memory usage

### Success Criteria

#### Automated Verification
- [ ] Timing logs appear in server output

#### Manual Verification
- [ ] Document optimal `MAX_PARALLEL_SCRAPES` value based on testing
- [ ] Confirm no rate limiting with chosen value
- [ ] Performance improvement quantified (e.g., "7-day scrape: 45s → 12s")

---

## Testing Strategy

### Unit Tests
- `scrape_single_source_for_date()` returns correct structure with mocked adapter
- Results are merged in deterministic source order regardless of completion order

### Integration Tests
- Parallel scrape produces same output as sequential for identical inputs
- Cache semantics unchanged (fresh dates skipped, stale dates rescraped)

### Manual Testing Steps
1. Cold cache 7-day scrape - verify all dates populated correctly
2. Warm cache 7-day scrape - verify only stale dates rescraped
3. Compare output payloads between sequential and parallel modes
4. Monitor external source response codes for rate limiting (429s)

## References

- Original two-level plan: `thoughts/26-01-25-scrape-parallelize-everything/followup.md`
- Plan review: `thoughts/26-01-25-scrape-parallelize-everything/followup.plan.review.md`
- Current service implementation: `tldr_service.py:156-254`
- Current parallel scraper: `newsletter_scraper.py:390-452`
