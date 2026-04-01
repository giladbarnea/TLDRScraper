---
status: completed
last_updated: 2026-04-01 18:05, a7219ee
---
# Flattened Single-Level Parallelism

Parallelized the backend scraping flow by replacing the sequential date loop with a single-level `ThreadPoolExecutor` architecture. Extracted a stateless `scrape_single_source_for_date()` worker and implemented global concurrency orchestration in `tldr_service.py` via a `MAX_PARALLEL_SCRAPES` environment variable. This allows concurrent processing of `(date, source)` work items while maintaining deterministic merge ordering and cache-first semantics. Removed redundant per-date parallelism and cleaned up obsolete environment variables.
