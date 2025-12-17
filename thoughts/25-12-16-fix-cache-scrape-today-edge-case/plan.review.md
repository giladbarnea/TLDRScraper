---
last_updated: 2025-12-17 14:08
---
# Plan Review - Cache-Scrape Edge Case (Today)

Summary of plan: the proposal suggests forcing the client to hit the server whenever the requested range includes today; the server would pull today's cached URLs, add them to `excluded_urls`, skip refetching those URLs, and return only new articles for the client to merge into Supabase.

Context reviewed: `client/src/lib/scraper.js` (cache check, mergeWithCache, stats flow), `storage_service.py`, `tldr_service.py`, `newsletter_scraper.py` (excluded_urls threading), `ARCHITECTURE.md` (scrape/cache flow + state machine).

Findings:
- Cached articles/issues would disappear on re-scrape. `mergeWithCache` only overlays state onto whatever articles the server returns and overwrites the stored payload; if the server returns "new only," all previously cached articles/issues for that date vanish and user state is lost (read/removed/TLDR/tldrHidden). Issues are not merged at all. This violates the stated invariants. (client/src/lib/scraper.js:118-164)
- Stats and issue metadata would be wrong. The client surfaces `data.stats` from the server even after merging, and issues are taken only from the latest payload. If the server sends only new rows, counts and issue groupings will no longer reflect the full dataset. (client/src/lib/scraper.js:118-126,203-210; newsletter_scraper.py:231-360)
- Past-date cache-first behavior regresses when today is in-range. Returning `false` from `isRangeCached` for any range containing today will re-scrape every date in that range (including already-cached past days), contradicting the invariant that past dates stay cache-first. Consider loading cached payloads for non-today dates and scraping only today. (client/src/lib/scraper.js:49-62,182-210)
- "Today" detection needs date-only normalization. Using `toISOString()`/`new Date()` directly can flip to tomorrow after local evening; a naive server check with `datetime.now()` would also fail because `_parse_date_range` yields midnight datetimes. Normalize to local (or UTC) date-only comparisons before deciding to bypass the cache. (client/src/components/ScrapeForm.jsx:22-33; tldr_service.py:19-42)
- Excluded URL set should be canonicalized/deduped when combining cached URLs with any caller-provided `excluded_urls` to avoid misses and unbounded list growth. (util.canonicalize_url; newsletter_scraper.py:231-360)

Recommendation: Consider revising the approach. We suggest updating the plan to keep cached articles/issues in the response (either union cached+new on the server and recompute stats, or make `mergeWithCache` union cached payloads and recalc stats) and to preserve cache-first for non-today dates while still forcing a fresh scrape for today. It might also be worth normalizing "today" checks to date-only values before bypassing the cache.
