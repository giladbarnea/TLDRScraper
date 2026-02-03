# Implementation: Cached-first background refresh

## Goal
Show cached newsletter payloads immediately after a session cache miss, then refresh in the background with `/api/scrape` so the UI is not blocked on a full scrape.

## Research summary
- `App.jsx` performs the initial two-day scrape and only renders after `/api/scrape` completes unless a 10-minute session cache hit occurs.
- `ScrapeForm.jsx` triggers a blocking scrape on submit and only renders after the request returns.
- `/api/storage/daily-range` already exists and is used by client storage helpers, so the cached payloads are available without adding new endpoints.

## Decisions made
### ✅ Cached prefetch before scrape
- **Decision:** If the 10-minute session cache is missed, fetch cached payloads via `/api/storage/daily-range` and render them immediately.
- **Rationale:** This preserves the current session cache fast-path while reducing empty UI time when cache exists in Supabase.

### ✅ Respect cache toggle
- **Decision:** Only prefetch cached payloads when `cache:enabled` is true.
- **Rationale:** The toggle advertises “Live Mode,” so showing cached data when disabled would be surprising.

### ✅ Keep `/api/scrape` as authoritative
- **Decision:** Always run `/api/scrape` after prefetch and replace results when it finishes.
- **Rationale:** The server is already responsible for freshness and merging user state; this keeps semantics intact.

## Decisions explicitly not taken
### ❌ New background refresh UI indicator
- **Reason:** The existing progress bar and “Syncing...” state already convey work in progress. Adding a new global indicator would add UI complexity without a clear benefit.

### ❌ Parallelized prefetch + scrape
- **Reason:** Prefetch is lightweight and sequential ordering keeps behavior deterministic, with minimal added latency.

## Implementation overview
- Added a client helper to fetch cached payloads via `storageApi.getDailyPayloadsRange` and return a consistent results shape.
- `App.jsx` now: session cache → optional cached prefetch → background scrape → update session cache.
- `ScrapeForm.jsx` now: optional cached prefetch → background scrape (existing flow).

## Notes
- No backend changes required.
- No changes to cache freshness rules (`cached_at` remains server-owned).
