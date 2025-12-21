---
status: completed
last_updated: 2025-12-21 10:12
---
# Fix Cache-Scrape Edge Case for Today

Fixed stale results when re-scraping today's date. Previously, client-side cache check returned immediately if today was cached, so new articles published later that day were invisible. Initial plan proposed server return "only new articles" — rejected because `mergeWithCache()` iterates incoming articles and overwrites the payload, deleting all previously cached articles and their user state (read/removed/tldr).

Solution: Server-side union. Client's `isRangeCached()` now returns `false` if today is in range, forcing server call. Server iterates dates individually: past dates use cache-first (load from Supabase, skip network); today loads cached articles, extracts their URLs to exclusion set, scrapes with those URLs excluded, then unions cached + new articles into complete payload. Stats recalculated from unified result. Existing `mergeWithCache()` works unchanged since server returns full payload.

Files: `tldr_service.py` (per-date iteration, union logic), `client/src/lib/scraper.js` (bypass cache when today in range).

COMPLETED SUCCESSFULLY.
