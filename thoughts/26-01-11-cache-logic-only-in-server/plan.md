# Plan: Consolidate cache logic on server

## Goal
- Move cache decisions and merge behavior entirely into the server so the client only requests data and renders it.

## Steps
1. Server: Add a new server-side response format for `/api/scrape` that returns daily payloads (date, articles, issues) in the client storage shape (camelCase, with `tldr`/`read` defaults). Include a feature flag or query param to select this response if needed.
2. Server: Move cache checks from client into server by integrating `storage_service.is_date_cached` and `storage_service.get_daily_payloads_range` inside the scrape flow, including the “today” union behavior.
3. Server: Ensure `/api/scrape` writes merged results to `daily_cache` (preserving existing `tldr`, `read`, `removed`) so the server owns merge semantics.
4. Client: Simplify `client/src/lib/scraper.js` to always call `/api/scrape` and remove cache-range checks, `loadFromCache`, and `mergeWithCache` logic.
5. Client: Keep `useSupabaseStorage` for reads/writes of user-driven state changes (e.g., `read`, `removed`) and TLDR updates.
6. Tests: Update or add tests for the scrape endpoint to cover cache hit, cache miss, and “today” union behavior, including preservation of `tldr`/`read`/`removed`.
