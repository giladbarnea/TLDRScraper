# Sync (date range) server-side flow + speed opportunities

## Server-side flow when the user clicks “sync” (scrape a date range)

### 1) HTTP entrypoint and request shape
* The UI sends a POST to `/api/scrape`. The Flask handler reads JSON, validates the optional `sources` array, and forwards `start_date`, `end_date`, `sources`, and `excluded_urls` (default `[]`) into the app layer via `tldr_app.scrape_newsletters`.【F:serve.py†L35-L68】
* `tldr_app.scrape_newsletters` is a thin pass-through to `tldr_service.scrape_newsletters_in_date_range`, keeping server-side logic in the service layer.【F:tldr_app.py†L10-L26】

### 2) Date-range validation and setup
* `tldr_service._parse_date_range` enforces required dates, ISO formatting, start <= end, and a max 31-day range. This is where invalid ranges are rejected early (ValueError).【F:tldr_service.py†L21-L44】
* The service builds a date list, computes “today” for special handling, and initializes tracking for articles, deduped URLs, issue metadata, and network fetch counts.【F:tldr_service.py†L81-L95】

### 3) Cache-first logic with “today” special case
* For each date, the service checks whether it’s today:
  * **Today:** it loads cached daily payload (Supabase), seeds results with cached articles + issues, then scrapes today *excluding* cached URLs, and merges new results. This means today always hits the network, but avoids refetching known URLs.【F:tldr_service.py†L96-L135】
  * **Past dates:** it tries cache first; if cached, it uses the cached payload. If not cached, it scrapes the date from the network.【F:tldr_service.py†L136-L166】
* Cache reads come from Supabase via `storage_service.get_daily_payload` (single-date query).【F:tldr_service.py†L101-L104】【F:storage_service.py†L32-L44】

### 4) Scrape execution mechanics
* Scraping a (date, source) combination is **fully sequential**: `scrape_date_range` loops over every date, then every source, calling `_collect_newsletters_for_date_from_source` per pair.【F:newsletter_scraper.py†L322-L363】
* `_collect_newsletters_for_date_from_source`:
  * Instantiates the adapter for the source ID.
  * Calls `adapter.scrape_date`.
  * Canonicalizes URLs, de-dupes against a shared `url_set`, and adds articles and issues.
  * Adds a **rate-limit sleep of 0.2s** when any network articles were returned.【F:newsletter_scraper.py†L267-L300】
* Final response assembly normalizes articles, groups by date, builds output markdown, and returns `articles`, `issues`, `stats`, etc.【F:newsletter_scraper.py†L201-L227】

## Low-hanging opportunities to make sync faster (server side)

### 1) Batch cache reads instead of per-date Supabase queries
* Right now, for each date in the range, the service calls `storage_service.get_daily_payload(date)` which is a separate Supabase round-trip per date.【F:tldr_service.py†L96-L138】【F:storage_service.py†L32-L44】
* There is already a range query helper (`get_daily_payloads_range`) that fetches all payloads between `start_date` and `end_date` in one request. Using it would eliminate N sequential Supabase reads for past ranges and likely reduce tail latency significantly.【F:storage_service.py†L61-L76】

### 2) Parallelize per-source scraping
* `scrape_date_range` processes (date, source) pairs serially with no concurrency. Each adapter call blocks the entire request, even when adapters are independent and likely IO-bound (network fetches).【F:newsletter_scraper.py†L322-L363】
* Introducing concurrency (e.g., per-date parallel source fetches with a small worker pool) is likely the biggest latency win, especially when many sources are configured.

### 3) Reduce or gate the fixed 0.2s per-source sleep
* `_collect_newsletters_for_date_from_source` sleeps 0.2s whenever it adds at least one new article from a source/date combination. With many sources, this can add seconds of artificial delay per request.【F:newsletter_scraper.py†L297-L300】
* If this is only needed for certain adapters or domains, you could move the delay into those adapters (or only sleep after a burst of requests), which would avoid penalizing every source uniformly.

---

# Three-phase plan (slow, careful, and simplest viable changes)

The plan intentionally starts with **parallel per-source scraping** because it is the most impactful and riskiest change (race conditions, shared state, and adapter assumptions). Next comes **batch cache reads** (simple but touches cache flow), and finally **rate-limit sleep tuning** (localized change once we understand concurrency behavior).

## Phase 1 — Parallelize per-source scraping (highest impact, highest risk)

### Before (sequential)
```
request
  -> scrape_date_range
      -> for date in dates
           -> for source in sources
                -> adapter.scrape_date (blocking)
                -> merge results
                -> sleep 0.2s if network
```

### After (bounded concurrency per date)
```
request
  -> scrape_date_range
      -> for date in dates
           -> submit N source tasks to worker pool
           -> await completion
           -> merge results in deterministic order
           -> (optional) per-source throttling
```

### Plan details (moving parts to account for)
1) **Establish a concurrency boundary**
   * Keep concurrency *per date* to avoid overwhelming upstream domains and to preserve the “date bucket” mental model.
   * Use a small worker pool sized for IO-bound tasks (e.g., 4–8 workers), not unbounded.
   * Ensure each worker receives immutable inputs: `date`, `source_id`, `excluded_urls`.

2) **Refactor `_collect_newsletters_for_date_from_source` to return results rather than mutating shared state**
   * Today it mutates `url_set`, `all_articles`, `issue_metadata_by_key`, and `processed_count` in-place.【F:newsletter_scraper.py†L234-L307】
   * For concurrency, return a structured payload: `{articles, issues, network_articles_count, errors}`.
   * Move canonicalization + de-dupe decisions into a single merge step in the parent thread to keep deterministic ordering and avoid shared-state races.

3) **Create a deterministic merge step**
   * Collect all per-source results for a date.
   * Merge into `url_set` and `all_articles` in a stable order (e.g., iterate sources in the original `source_ids` order).
   * Preserve existing logic around `issue_metadata_by_key` (triple-key) during merge.【F:newsletter_scraper.py†L289-L296】

4) **Confirm adapter safety**
   * Each adapter should be stateless per call; if any adapter uses global or cached state, confirm it is thread-safe (or wrap it).
   * Keep adapter instantiation inside the worker to avoid shared objects.

5) **Telemetry and guardrails**
   * Extend logging around per-source task start/finish to diagnose failures without serial behavior.
   * Ensure exceptions inside a worker are captured and logged (do not fail the entire scrape unless needed).

6) **Validation (upstream & downstream)**
   * Verify that response format (articles/issues/stats/output) is unchanged.
   * Confirm that downstream cache merge and UI parsing are unaffected.

---

## Phase 2 — Batch cache reads for date ranges (low complexity, moderate benefit)

### Before (per-date Supabase calls)
```
for date in dates:
  payload = get_daily_payload(date)
  if payload: use cache
  else: scrape
```

### After (single range call + lookup)
```
cache_payloads = get_daily_payloads_range(start_date, end_date)
cache_map = {payload.date: payload}
for date in dates:
  if date in cache_map: use cache
  else: scrape
```

### Plan details (moving parts to account for)
1) **Fetch once, index locally**
   * Use `storage_service.get_daily_payloads_range` to retrieve all cached payloads in one query.【F:storage_service.py†L61-L76】
   * Build a `dict` keyed by `date` so lookups are O(1).

2) **Maintain “today” special-case semantics**
   * Today should still be unioned with live scrape using cached URLs (exclude cached URLs during scrape).【F:tldr_service.py†L99-L130】
   * Ensure that the cached payload for today comes from the range map rather than a per-date call.

3) **Keep cache-miss behavior identical**
   * If a date is missing from the cache map, fall back to `scrape_date_range` (no behavior change for missing dates).

4) **Validate payload shape assumptions**
   * `get_daily_payloads_range` returns payload objects (not rows) — ensure the returned objects still contain `date` to index correctly.【F:storage_service.py†L61-L76】

---

## Phase 3 — Reduce or gate the fixed 0.2s sleep

### Before
```
if network_articles > 0:
  time.sleep(0.2)
```

### After (more targeted throttling)
```
if adapter_requires_throttle:
  throttle_strategy.maybe_sleep()
```

### Plan details (moving parts to account for)
1) **Identify adapters that truly need throttling**
   * Some sources may already be rate-limited by upstream or are static pages; sleeping after every fetch is unnecessary overhead.
   * Move the sleep into adapters that require it, or apply a per-domain throttler.

2) **Avoid penalizing concurrency**
   * Under parallel execution, a global sleep could negate parallel gains.
   * Implement throttling as a lightweight, per-adapter policy with a shared limiter if needed.

3) **Keep behavior simple and explicit**
   * Prefer a small mapping (e.g., `THROTTLED_SOURCES`) over complex heuristics.
   * Ensure that removing or reducing sleep does not increase error rates (watch logs).

