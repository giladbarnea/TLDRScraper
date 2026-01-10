# Plan: Mitigate N+1 Supabase fetches on page load

## Problem
The initial `loadFromCache` request fetches a date range, but each rendered day still triggers `useSupabaseStorage` to fetch `/api/storage/daily/<date>` again. This N+1 behavior adds redundant network and Supabase calls on page load.

## Goals
- Reuse the already-fetched daily payloads from the date-range response.
- Avoid per-day fetches when data is already available in memory.
- Keep existing storage API endpoints and cache behavior intact.

## Approach
1. Export a small cache-priming helper from `client/src/hooks/useSupabaseStorage.js` that seeds the in-memory `readCache` for a given key.
2. After `loadFromCache` retrieves payloads, prime the cache for each date using `getNewsletterScrapeKey(date)` so subsequent `useSupabaseStorage` reads hit the cache and skip network calls.
3. Ensure no behavior changes for cache misses or real-time updates.

## Files to update
- `client/src/hooks/useSupabaseStorage.js`: add a named export to prime the `readCache` for a key.
- `client/src/lib/scraper.js`: import the helper and `getNewsletterScrapeKey`, then prime the cache inside `loadFromCache`.
