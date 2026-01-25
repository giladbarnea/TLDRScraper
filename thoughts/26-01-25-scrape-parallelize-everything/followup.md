---
last_updated: 2026-01-25 11:53, cb6c5e1
---
# Follow-up Plan: Two-Level Scrape Parallelism

## Goal
Enable two-level concurrency in the backend scrape flow:
1) **Per-date parallelism** for `ScrapeRange` (dates in range).
2) **Per-source parallelism** for `ScrapeDay` (sources for a date).

This matches the conceptual model:

```
ScrapeRange(range) {
  With workers(workers=len(range)) {
    ScrapeDay(individual day)
  }
}

ScrapeDay(day) {
  With workers(workers=len(newsletter_sources)) {
    ScrapeSource(newsletter_source)
  }
}
```

## Current State
- **Per-source parallelism (per day)** is already implemented in `newsletter_scraper.py` via `ThreadPoolExecutor` and deterministic merging.
- **Per-date parallelism** is not present. `scrape_date_range` iterates dates sequentially.
- The cache logic in `tldr_service.py` already batches cache reads and performs scrape + merge per day.

## Design Approach
### A) Add date-level parallelism in the service layer
Implement concurrency at the date iteration in `tldr_service.scrape_newsletters_in_date_range` rather than inside `newsletter_scraper.scrape_date_range`. This keeps cache merging and payload assembly centralized and consistent.

### B) Keep source-level parallelism inside `scrape_date_range`
Maintain existing per-date, per-source parallel execution as-is, so each date worker uses the same deterministic merge path.

### C) Preserve deterministic ordering and cache semantics
- Date results must be assembled in the original date order (descending by date).
- Maintain existing cache-first/merge logic, including exclusion of cached URLs during rescrapes.
- Preserve read/tldr/removed state via existing `_merge_payloads` logic.

## Step-by-Step Plan

### Step 1: Add a date-level worker function
Add a helper in `tldr_service.py` that processes a single date end-to-end:
- Inputs: `date`, `date_str`, `cache_row`, `source_ids`, `excluded_urls`.
- Decide whether to use cache or rescrape (existing logic).
- Return: `{date_str, payload, did_scrape, network_fetches}`.

This function should not mutate shared structures. It must be pure-ish (data in, data out) so it can run in parallel.

### Step 2: Add a date-level thread pool
In `scrape_newsletters_in_date_range`:
- Build the date list (already done).
- Spin up a `ThreadPoolExecutor` with `max_workers = len(dates)` (or a capped value) to run per-date workers.
- Collect results and reorder by the original date sequence.

Guardrails:
- Provide a feature flag (e.g., `ENABLE_PARALLEL_DATES`) and a `SCRAPER_MAX_DATE_WORKERS` env var.
- Default to existing sequential flow if disabled.

### Step 3: Preserve cache writes in the main thread
Keep writes to Supabase in the main thread after collecting results.
- This avoids multiple threads writing the same row and keeps logging deterministic.
- Use the existing write function for scraped dates only.

### Step 4: Update stats deterministically
Aggregate `total_network_fetches` from per-date results.
Compute stats from the final ordered payloads, exactly as done today.

### Step 5: Validate ordering + equivalence
- Verify output payload ordering matches current behavior (date descending).
- Validate that per-date results are the same as sequential mode on a fixed set of inputs.

## Test Plan
1) **Unit-style tests** (if possible):
   - Validate that date-level parallelism returns the same payloads as sequential mode for a stubbed scraper.
2) **Manual sanity checks**:
   - Run `/api/scrape` for a 3-day range with parallel dates enabled and disabled; compare article counts and payload shapes.
   - Confirm cache hit behavior is unchanged (no unintended rescrapes).

## Risks & Mitigations
- **Thread safety of Supabase client**: keep writes in main thread.
- **Over-parallelization**: cap date workers (`min(len(dates), 4 or 8)`) to avoid saturating upstream sources.
- **Adapter assumptions**: already validated for per-source parallelism; date-level parallelism does not share adapter instances.

## Notes
- Keep concurrency boundaries clear:
  - Date-level workers run in `tldr_service`.
  - Source-level workers run in `newsletter_scraper`.
- Avoid embedding fallback-heavy logic. Assume upstream data is valid.
