---
last_updated: 2026-04-01 10:17
---
# Cold Refresh Performance Analysis: State 2

## Context & Scope
The goal of this investigation is to study the domains affecting the web page *COLD refresh performance*, specifically targeting **State 2**: Data is scraped and exists in Supabase, but is not cached on the client (via `sessionStorage` or `localStorage`).

The client cache was artificially disabled during testing by setting `sessionStorage.getItem()` to `null` to ensure consistent cold-starts from the client's perspective.

To fulfill the requirements, target dates (the last 3 days) were populated in Supabase first (State 1 fulfilled).

## Reproducing the Problem & Initial Measurements
With the client cache disabled, the application would initialize `Feed` data by making two calls concurrently on page mount:
1. `getDailyPayloadsRange` (fetch `daily-range` from Supabase)
2. `scrapeNewsletters` (trigger heavy background scraping)

### Server Performance (Isolated)
When testing the endpoints cleanly against the Python Flask backend:
- `/api/storage/daily-range` returns in **~0.25 - 0.6 seconds** (depending on date range).
- `/api/scrape` returns in **~5.7 - 10.8 seconds**.

### Client Performance & Issue (Concurrent Calls)
When measuring the frontend using Playwright headless evaluations over `http://localhost:3000`:
- **Load Time (Time-to-first-article)**: `~5.85 seconds`

**The Root Cause**: Because `getDailyPayloadsRange` and `scrapeNewsletters` were dispatched concurrently at the exact same moment on mount, the browser and Python server attempted to execute both at the same time. The heavy `scrapeNewsletters` operation introduces severe backend thread/GIL contention. This caused the inherently fast `daily-range` endpoint to queue up behind the intensive scraping operation, forcing the client to wait the entire duration of `scrapeNewsletters` before receiving the cached payloads to render the DOM. 

## The Pattern to Solve It: Prioritized API Hydration
To eliminate the "few long seconds" of wait time, I migrated the data-fetching mechanism from a **Concurrent Fire-and-Forget Pattern** to **Sequential Prioritized Hydration**:

1. **Await the Critical Path**: Fetch and await `/api/storage/daily-range` *first*. Since no simultaneous scraping occurs, the backend fulfills this request unhindered.
2. **Immediate Rendering**: The UI is updated seamlessly using the Supabase payload. Users perceive instantaneous loading and can begin reading right away. 
3. **Background Sync**: Only *after* rendering the existing data do we trigger `scrapeNewsletters` so new articles are seamlessly merged without blocking user interactions or rendering.

## Iterating and Final Measurements
After modifying `App.jsx` to fetch sequentially:
```javascript
// Phase 1: render cached data immediately
const cachedPayloads = await getDailyPayloadsRange(startDate, endDate, signal).catch(() => [])
// ... UI updates ...

// Phase 2: merge background scrape results
const result = await scrapeNewsletters(startDate, endDate, signal)
```

Playwright metrics confirmed the expected improvement:
- **Load Time (Time-to-first-article)**: `~0.72 seconds`
- `daily-range` Waterfall: Started at `191.3ms`, Duration `525ms`, concluding rendering.
- `scrape` Waterfall: Scheduled after the DOM updates, cleanly hiding the ~5 seconds HTTP request in the absolute background.

By resolving the backend contention and prioritizing the database-read stream, the cold-refresh in State 2 is practically indistinguishable from State 3 (Client Cache).
