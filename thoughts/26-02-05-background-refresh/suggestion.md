# Suggestion: Background refresh with cached-first UI

## Context (what I think the system is doing today)
- The client boot path in `App.jsx` uses a 10-minute session cache; when that misses it waits for `/api/scrape` to finish before rendering results, so the UI stays empty during the server scrape. This looks like a single blocking fetch from the user's point of view. I might be missing a detail, but that is how it reads today. 
- The UI already has a cache-seeding path in `useSupabaseStorage`: when `CalendarDay` mounts, the payload passed from `/api/scrape` seeds the in-memory cache so downstream hooks avoid extra network reads. 
- The backend owns cache freshness and rescrape decisions (based on `cached_at`), and `/api/scrape` already merges cached user state into the returned payloads before writing back to Supabase.

## What I think we want
Make the UI show *anything* already available in Supabase for the requested date range **before** any rescrape completes, then refresh in the background and update the UI when the scrape finishes.

## A possible approach (tentative)
1. **Add a “cached-first prefetch” step in the client**
   - When a range is requested (initial load or form submit), first call `/api/storage/daily-range` to get cached payloads for that range.
   - If cached payloads exist, set `results` immediately to those payloads so the feed renders with what is already known.
   - This preserves the 10-minute session cache as the fastest path; the prefetch only runs on a session cache miss.

2. **Kick off `/api/scrape` in the background (non-blocking)**
   - After the cached payloads are displayed, start the existing `/api/scrape` request.
   - When it completes, replace `results` with the returned payloads (which already include merged read/removed/tldr state), and update the session cache timestamp.
   - This should keep the current storage-state guarantees intact because the server is still the only place deciding freshness and performing merges.

3. **Keep UI cues small and consistent**
   - The existing “Syncing...” indicators can keep signaling per-day storage updates via `useSupabaseStorage` if needed.
   - If we want a global indicator, it might be enough to reuse the form’s progress bar or add a subtle “Refreshing…” pill while the background scrape is in flight.

## Why this seems to fit the current state machines (tentative mapping)
- **Scrape state machine**: instead of “validating → fetching_api → complete”, we could insert a “prefetch_cached” state that yields a partial UI, then continue into the existing fetch path. That still ends in the same `complete` state with the authoritative payloads. 
- **Storage/state hooks**: cached payloads rendered via `CalendarDay` should seed the `useSupabaseStorage` cache the same way live payloads do today, so `useArticleState` and `useSummary` keep their optimistic update behavior.
- **Backend cache semantics** remain unchanged: `/api/scrape` still owns rescrape logic, merges cached user state, and writes `cached_at` only for scrape-driven updates.

## Risks / questions I am not fully certain about
- **Cache-enabled toggle semantics**: the client still passes a `cacheEnabled` value but doesn’t appear to send it to the server; I’m not sure if we want to gate cached prefetch on that toggle, or if it should always run for fast UI.
- **Partial ranges**: showing only some cached dates could look odd if the range is large and the cache is sparse. If that’s a concern, we could display a small “partial data” callout or placeholder rows for missing dates.
- **Session vs local storage**: the current 10-minute cache is in `sessionStorage`, not `localStorage`. If we rely on this for fast re-entry, maybe that is enough; if we want cross-tab or longer-lived caching, that might be a separate decision.

## Minimal implementation sketch (non-binding)
- Add a helper in `client/src/lib/scraper.js` (or a new helper in `storageApi.js`) that calls `/api/storage/daily-range` and returns `{ payloads, source: 'cache' }`.
- In `App.jsx` and `ScrapeForm.jsx`, on range submission:
  1. Try session cache; if hit, render and optionally skip background refresh (or still refresh if we want).
  2. If miss, fetch cached range and render it immediately if non-empty.
  3. Start `/api/scrape` and update results when it finishes.

If this direction sounds right, I can outline a more concrete plan or draft a small patch that wires the prefetch into the existing flow.
