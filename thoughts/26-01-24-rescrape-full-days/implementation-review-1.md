---
last_updated: 2026-01-25 11:53, cb6c5e1
---
# Implementation Review 1 - Rescrape Full Days

## Scope reviewed
- Cache read/write plumbing and route adjustments (`storage_service.py`, `serve.py`).
- Cache freshness logic and rescrape flow (`tldr_service.py`, `util.py`).
- Updated server-side cache tests (`tests/test_scrape_cache_server.py`).

## Recommendations

1. **Reduce repeated date formatting lookups in the fast-path cache check.**
   In `scrape_newsletters_in_date_range`, `util.format_date_for_url(d)` is called multiple times per date (fast-path `all_cached_and_fresh` and again when building `ordered`). This can be simplified by precomputing a `date_strings = [util.format_date_for_url(d) for d in dates]` list and using it for the cache checks and ordering. This reduces duplicated work and makes the logic easier to scan without changing behavior. (`tldr_service.py`).

2. **Collapse parallel cache maps into a single structure.**
   The code currently builds `cache_map` and `cached_at_map` separately, which requires two lookups each time a date is consulted and risks them drifting apart. A single dict like `cache_rows[date_str] = {"payload": ..., "cached_at": ...}` would keep related data together and reduce cognitive overhead in the rescrape loop. This should make the loop logic shorter and easier to reason about. (`tldr_service.py`).

3. **Document the new daily-range return shape.**
   The `get_daily_payloads_range` helper now returns rows that include `cached_at`, while the `/api/storage/daily-range` route maps those to payloads before returning. Consider updating the architecture or storage documentation so future readers know the helper returns `{date, payload, cached_at}` rows and the API still returns payloads. This avoids confusion if someone assumes the helper still returns payloads directly. (`storage_service.py`, `serve.py`, `ARCHITECTURE.md`).
