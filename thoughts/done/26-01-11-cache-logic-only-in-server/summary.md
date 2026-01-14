---
status: completed
last_updated: 2026-01-14 07:20, 6edf97f
---
# Server-Side Cache Consolidation

Moved cache logic from client to server. Server now owns all cache decisions: full cache hit returns early without scraping (tldr_service.py:174-188), cache miss scrapes and writes to daily_cache (lines 219-230), today always unions fresh with cached articles while preserving tldr/read/removed state (lines 193-217). Implemented payload merge semantics (_merge_payloads at lines 85-128) and default article state builders (_build_default_article_state at lines 47-57). Client simplified to single fetch call (client/src/lib/scraper.js:6-29) with all cache/merge logic removed. Storage service provides is_date_cached, get_daily_payload, set_daily_payload, and get_daily_payloads_range for server-side operations.

COMPLETED SUCCESSFULLY.
