---
last_updated: 2026-01-25 15:30
---
# Plan Review: Two-Level Scrape Parallelism

## Summary

The plan proposes adding **date-level parallelism** to the scrape flow by introducing a `ThreadPoolExecutor` in `tldr_service.py`, creating a two-tiered parallel architecture:

1. **Outer level (new)**: Parallel date processing in `tldr_service.scrape_newsletters_in_date_range()`
2. **Inner level (existing)**: Parallel source processing in `newsletter_scraper.scrape_date_range()`

The goal is to reduce wall-clock time for multi-day scrapes by processing dates concurrently.

---

## Codebase Research

I analyzed the following key flows:

### Current Architecture

```
tldr_service.scrape_newsletters_in_date_range()          ← Sequential date iteration
  └─ for current_date in dates:
       └─ newsletter_scraper.scrape_date_range(date, date, ...)  ← Called per-date
            └─ ThreadPoolExecutor(max_workers)           ← Parallel source iteration
                 └─ adapter.scrape_date(date, excluded)  ← HTTP fetches
```

**Key observations:**

1. **`tldr_service.py:156-254`**: Orchestrates date iteration, cache decisions, and payload merging. Calls `scrape_date_range(current_date, current_date, ...)` with a **single date** each time.

2. **`newsletter_scraper.py:503-595`**: Despite its name, `scrape_date_range()` is always called with `start == end` from the service layer. The per-date parallelism lives here via `ThreadPoolExecutor`.

3. **Cache semantics**: The service layer does a single batch cache read upfront (`get_daily_payloads_range`), then decides per-date whether to use cache or rescrape based on `util.should_rescrape()`.

4. **Deterministic ordering**: Source results are merged in original `source_ids` order despite parallel execution.

---

## Assessment

The plan is **well-structured and thoughtful**. It:
- Keeps date-level logic in `tldr_service` (maintains layer boundaries)
- Proposes pure-ish date workers (parallelizable)
- Preserves cache writes in the main thread (avoids races)
- Adds feature flags for gradual rollout

However, I have concerns about whether this is the right architectural direction.

---

## Concerns

### 1. Does the problem actually exist?

The plan assumes date-level parallelism will meaningfully improve performance. But for typical usage:

| Scenario | Cache state | Benefit of date parallelism |
|----------|-------------|----------------------------|
| Scrape today only | N/A | None (single date) |
| Scrape past 7 days | 6 cached, 1 fresh | Minimal (only 1 date needs work) |
| Scrape past 7 days (cold cache) | All fresh | Real benefit, but rare |
| Rescrape due to stale cache | 1-2 dates stale | Minimal |

The **common case** (today + cached past) doesn't benefit from date-level parallelism. The rare cold-cache case does, but at what complexity cost?

**Suggestion**: Before implementing, measure actual wall-clock time for a 7-day cold-cache scrape. Is date iteration the bottleneck, or is it external API rate limits and network latency (which parallelism may make worse)?

### 2. Two-level parallelism introduces multiplicative complexity

With nested `ThreadPoolExecutor`s:

```
Total concurrent threads = date_workers × source_workers_per_date
```

If `SCRAPER_MAX_DATE_WORKERS=7` and `SCRAPER_MAX_WORKERS=25`, you could have **175 concurrent network requests**. This likely triggers rate limiting from external sources (TLDR archives, HN Algolia API, etc.) and may actually **hurt** performance.

The plan mentions capping workers, but there's **no global concurrency cap** across both levels. Each date worker spawns its own source worker pool independently.

### 3. Harder to reason about and debug

Two nested thread pools means:
- Thread starvation becomes possible if pools contend
- Stack traces become harder to follow
- Timeouts and error handling must work correctly at both levels
- Testing requires more complex fixtures

---

## Alternative: Flatten to Single-Level Parallelism

A staff engineer might ask: **"Could we achieve the same goal with less complexity?"**

Instead of nested parallelism, flatten the work into (date, source) tuples with a **single global worker pool**:

```python
def scrape_newsletters_in_date_range(start, end, source_ids, excluded_urls):
    # 1. Bulk fetch cache (existing)
    cache_map = storage_service.get_daily_payloads_range(start, end)

    # 2. Build flat work items: only (date, source) pairs that need scraping
    work_items = []
    for date in dates:
        if should_rescrape(date, cache_map):
            cached_urls = extract_cached_urls(cache_map.get(date))
            for source_id in source_ids:
                work_items.append((date, source_id, cached_urls))

    # 3. Single-level parallelism with global cap
    results = defaultdict(list)
    with ThreadPoolExecutor(max_workers=GLOBAL_MAX_WORKERS) as pool:
        futures = {pool.submit(scrape_single, item): item for item in work_items}
        for future in as_completed(futures):
            date, source_id, articles, issues = future.result()
            results[date].append((source_id, articles, issues))

    # 4. Merge with cache and write (sequential, deterministic)
    for date in dates:
        merged = merge_results(results[date], cache_map.get(date))
        storage_service.set_daily_payload_from_scrape(date, merged)

    return build_response(...)
```

**Advantages:**
- **Single global cap**: `GLOBAL_MAX_WORKERS=20` means exactly 20 concurrent requests, period
- **Better load balancing**: Workers grab next available work item, no per-date grouping inefficiency
- **Simpler error handling**: One pool to manage
- **Easier to reason about**: Linear work queue, no nesting
- **Preserves determinism**: Merge by source order after collection

**Trade-off**: This restructures the boundary between `tldr_service` and `newsletter_scraper`. The parallelism moves fully into the service layer. But this may actually be cleaner—`tldr_service` is already the orchestration layer; `newsletter_scraper` can become a simple single-(date, source) scraper.

---

## Other Observations

### The `scrape_date_range` naming is misleading

The function is **always** called with a single date from `tldr_service`. It doesn't actually process a range—it processes one date. This suggests the abstraction boundary between layers could be cleaner.

A refactor might rename or restructure:
- `scrape_date_range(date, date, ...)` → `scrape_single_date(date, ...)`
- Move range orchestration fully into `tldr_service`

### Feature flags add surface area

The plan proposes `ENABLE_PARALLEL_DATES` and `SCRAPER_MAX_DATE_WORKERS` env vars. Combined with existing `ENABLE_PARALLEL_SCRAPING` and `SCRAPER_MAX_WORKERS`, that's four parallelism knobs to tune. Consider whether fewer, more meaningful controls would suffice (e.g., a single `SCRAPER_MAX_CONCURRENT_REQUESTS`).

---

## Final Recommendation

**Approve with significant modifications.**

The goal (faster multi-day scrapes) is valid, but the approach (nested thread pools) may be over-engineered for the actual problem. Before implementing:

1. **Measure first**: Profile a 7-day cold-cache scrape. Is date iteration actually the bottleneck?

2. **Consider the flattened approach**: Single-level parallelism with (date, source) work items is simpler and provides a global concurrency cap.

3. **If two-level parallelism is preferred**, add a **global concurrency semaphore** shared between date and source workers to prevent thread explosion:
   ```python
   GLOBAL_SEMAPHORE = threading.Semaphore(MAX_TOTAL_CONCURRENT)
   ```

4. **Start with conservative defaults**: `MAX_DATE_WORKERS=4`, not `len(dates)`. External APIs will rate-limit aggressive parallelism.

The plan demonstrates good understanding of the system's invariants (deterministic ordering, cache semantics, thread-safe writes). The concerns are about choosing the simplest architecture that achieves the goal—not about correctness.
