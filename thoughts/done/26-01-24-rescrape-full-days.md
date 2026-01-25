---
status: completed
last_updated: 2026-01-24
---
# Rescrape Full Days

Reworked cache freshness so every day rescrapes until after the next midnight in America/Los_Angeles, using `daily_cache.cached_at` as the scrape timestamp. Added a scrape-only write path to update `cached_at` and a unified rescrape check, removing the "today" special case while preserving merge semantics.
