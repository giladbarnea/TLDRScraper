---
last_updated: 2026-02-06 11:43, 6fd30cd
---
# Background Rescrape Design

## Problem

When the page loads, `App.jsx` calls `POST /api/scrape` which blocks the entire render until the server finishes scraping. For "today," the server always rescrapes (because `should_rescrape()` returns `True` for the current day — the cache is never "fresh enough" until tomorrow's midnight Pacific). This network round-trip to 20+ external sources takes 3-15 seconds, during which the user sees only a pulsing skeleton placeholder.

Meanwhile, cached articles from previous scrapes for today (and the past two days) already exist in Supabase's `daily_cache` table and could be shown immediately.

## Desired Behavior

1. Display cached articles instantly on page load
2. Rescrape stale dates (today) in the background
3. When new articles arrive, merge them into the live display without a full re-render or page reload

## Design

### Two-Phase Load

**Phase 1 — Immediate render from cache** (~100ms)

Fetch cached payloads from Supabase via the existing `POST /api/storage/daily-range` endpoint. If data exists, set `results` state → UI renders immediately with articles from the last scrape.

**Phase 2 — Background rescrape** (3-15s, non-blocking)

Fire `POST /api/scrape` concurrently. When it completes, merge fresh payloads into the already-rendered data using the existing `useSupabaseStorage` pub/sub system. New articles appear; existing articles keep their local user state.

### Why This Works

The infrastructure already exists:

- `POST /api/storage/daily-range` (`serve.py:186`) returns cached payloads as a flat array
- `storageApi.getDailyPayloadsRange()` (`storageApi.js:39`) is the client function that calls it
- `useSupabaseStorage` has module-level `readCache` and `emitChange` that power cross-component reactivity
- CalendarDay seeds `readCache` on mount; all `useArticleState` hooks subscribe to the same key
- The server's `_merge_payloads()` (`tldr_service.py:91`) already unions cached + new articles while preserving `tldr`/`read`/`removed` state

The only new code needed: a `mergeIntoCache` export from `useSupabaseStorage.js`, and a rewrite of the `useEffect` in `App.jsx`.

## Detailed Flow

### On Mount (App.jsx useEffect)

```
1. Compute date range (today-2 through today)
2. Check sessionStorage TTL cache → if hit, setResults, done
3. If cache miss:
   a. Start both requests concurrently:
      - cachePromise = storageApi.getDailyPayloadsRange(startDate, endDate, signal)
      - scrapePromise = scrapeNewsletters(startDate, endDate, signal)

   b. Await cachePromise:
      - If payloads non-empty → setResults({ payloads, stats: null, source: 'cache' })
        → UI renders with cached articles
      - If empty → do nothing yet (skeleton stays, wait for scrape)

   c. Await scrapePromise:
      - If phase 1 rendered data:
        → For each fresh payload, call mergeIntoCache(key, mergeFn)
        → Update results.stats with fresh stats
      - If phase 1 was empty:
        → setResults(scrapeResult) (same as current behavior)

   d. Write final results to sessionStorage cache
```

Both requests fire immediately. The cache read returns in ~100ms; the scrape takes seconds. The user sees articles after ~100ms; new articles merge in when the scrape finishes.

### First-Ever Visit (No Cache)

Phase 1 returns empty payloads. The skeleton stays visible. Phase 2 completes, `setResults` is called, UI renders — identical to current behavior. No regression.

### sessionStorage Hit (Within 10-Minute TTL)

Unchanged. The cached result is used directly, skipping both phases. No regression.

## New Code: `mergeIntoCache`

Export from `useSupabaseStorage.js`:

```js
export function mergeIntoCache(key, mergeFn) {
  const current = readCache.get(key)
  const merged = mergeFn(current)
  if (merged === current) return
  readCache.set(key, merged)
  emitChange(key)
}
```

This is a "write to the in-memory cache and notify all subscribers" primitive. It does not persist to the server — the server already wrote the merged payload during the scrape (via `set_daily_payload_from_scrape`).

**Why no server write?** The scrape endpoint already persists the fully merged result to `daily_cache` with an updated `cached_at`. Writing again from the client would be redundant. User state changes continue to persist through the normal `setValueAsync` → `writeValue` path.

## Client-Side Merge Function

When the background scrape response arrives, for each date's fresh payload:

```js
import { getNewsletterScrapeKey } from './lib/storageKeys'
import { mergeIntoCache } from './hooks/useSupabaseStorage'

function applyBackgroundScrapeResults(freshPayloads) {
  for (const freshPayload of freshPayloads) {
    const key = getNewsletterScrapeKey(freshPayload.date)

    mergeIntoCache(key, (localPayload) => {
      if (!localPayload) return freshPayload

      // Build lookup of local user state by URL
      const localByUrl = new Map(
        localPayload.articles.map(a => [a.url, a])
      )

      // For articles the server returned, overlay any local user state
      const mergedArticles = freshPayload.articles.map(article => {
        const local = localByUrl.get(article.url)
        if (!local) return article  // New article from scrape
        return {
          ...article,
          tldr: local.tldr,
          read: local.read,
          removed: local.removed,
        }
      })

      return { ...freshPayload, articles: mergedArticles }
    })
  }
}
```

**Why overlay local user state?** Between phase 1 rendering and phase 2 completing, the user may have interacted with articles (mark read, remove, fetch summary). Those changes live in `readCache` and may or may not have been persisted to Supabase yet. The server's scrape reads from Supabase, so it might have stale user state for articles the user just modified. The merge preserves the client's version (which is always equal to or newer than the server's).

**Why the server's payload is a superset:** The server's `_merge_payloads()` (`tldr_service.py:91-134`) unions all cached articles with newly scraped articles. The fresh payload contains every article that was in the cache plus any new ones. We only need to overlay local state, not worry about missing articles.

## What Triggers UI Updates

After `mergeIntoCache(key, mergeFn)` updates `readCache` and calls `emitChange(key)`:

1. All `useSupabaseStorage` instances subscribed to that key have their `handleChange` listener fire (`useSupabaseStorage.js:195`)
2. Each listener calls `readValue(key)`, which hits `readCache` (line 44) and returns the merged payload
3. `setValue(newValue)` triggers React re-renders
4. CalendarDay re-derives `articles` and `issues` from the new `livePayload`
5. New articles appear in the list; existing articles keep their visual state

No special re-mounting. No prop drilling. The existing pub/sub system handles it.

## Race Condition Analysis

### Timeline: User modifies article during background scrape

```
t=0   Phase 1 renders cached data (article B unread)
t=0   Background scrape request fires (server reads DB: B unread)
t=1   User marks B as read → optimistic local update + async write to Supabase
t=3   Server finishes scraping (used snapshot from t=0, has B unread in response)
t=3   Client merges: overlays local state → B stays read ✓
```

The client-side merge function resolves this: it always prefers local user state over the server's response. The server's payload provides the article list (including new articles); the client provides the freshest user state.

### What about the database?

The scrape writes the merged payload (with B unread) via `set_daily_payload_from_scrape`. The user's write (B read) may arrive before or after the scrape's write:

- **User write arrives first → scrape write overwrites → B unread in DB.** On next page load, B would appear unread. The user's next interaction with any article on that date triggers a full payload write (via `set_daily_payload`), restoring B's read state.
- **Scrape write arrives first → user write overwrites → B read in DB.** Correct.

The first scenario is a narrow race window (the user must interact during the 3-15s scrape window, and the writes must interleave unfavorably). The consequence is minor — a read marker might be lost until the next interaction. For a newsletter reader, this is an acceptable tradeoff for the dramatic UX improvement.

**Mitigation if desired later:** After `mergeIntoCache`, trigger a `writeValue` for dates where local state differed from the server's response. This reconciles the DB. Not needed for v1.

## Edge Cases

| Scenario | Behavior |
|---|---|
| First visit (no cache) | Phase 1 empty → skeleton → phase 2 renders normally |
| All dates fully cached & fresh | Server returns from fast-path (`source: "cache"`), phase 2 completes quickly, no visible change |
| sessionStorage hit (< 10 min) | Both phases skipped, use cached result directly |
| Phase 1 fails (network error) | Swallow error, fall through to phase 2 (acts like current behavior) |
| Phase 2 fails (network error) | If phase 1 rendered data, keep it. If not, show error state |
| Component unmounts during load | AbortController cancels both requests |
| Manual scrape from ScrapeForm | Unchanged — `onResults` calls `setResults`, overwriting everything |
| New articles found by scrape | Appear in the list via `mergeIntoCache` → pub/sub → re-render |
| No new articles found | `mergeIntoCache` receives same article set, merge is a no-op if user state matches |

## Files to Change

| File | Change |
|---|---|
| `client/src/hooks/useSupabaseStorage.js` | Export `mergeIntoCache(key, mergeFn)` (~5 lines) |
| `client/src/App.jsx` | Rewrite `useEffect` to two-phase load (~40 lines) |

## What's NOT Changing

- **Server-side scrape logic** — no changes to `tldr_service.py`, `serve.py`, or `storage_service.py`
- **`useSupabaseStorage` hook behavior** — the hook itself is untouched; we only add a module-level export
- **CalendarDay, Feed, ArticleCard** — no component changes
- **`scraper.js`** — the `scrapeNewsletters` function is used as-is
- **`storageApi.js`** — `getDailyPayloadsRange` is used as-is (already exists at line 39)
- **Cache-seeding mechanism** — CalendarDay still seeds `readCache` on mount with the payload prop
- **sessionStorage cache** — same TTL, same key format, same behavior
- **Manual scrape via ScrapeForm** — unchanged

## Pseudocode: Revised App.jsx useEffect

```js
useEffect(() => {
  const controller = new AbortController()
  const { signal } = controller

  const today = new Date()
  const twoDaysAgo = new Date(today)
  twoDaysAgo.setDate(today.getDate() - 2)
  const endDate = today.toISOString().split('T')[0]
  const startDate = twoDaysAgo.toISOString().split('T')[0]

  const cacheKey = `scrapeResults:${startDate}:${endDate}`
  const TTL_MS = 10 * 60 * 1000

  // 1. sessionStorage fast path (unchanged)
  const cached = sessionStorage.getItem(cacheKey)
  if (cached) {
    const { timestamp, data } = JSON.parse(cached)
    if (Date.now() - timestamp < TTL_MS) {
      setResults(data)
      return
    }
  }

  // 2. Two-phase load
  let phase1Rendered = false

  // Start both requests concurrently
  const cachePromise = getDailyPayloadsRange(startDate, endDate, signal)
    .catch(() => [])  // Phase 1 failure is non-fatal

  const scrapePromise = scrapeNewsletters(startDate, endDate, signal)

  // Phase 1: render cached data immediately
  cachePromise.then(payloads => {
    if (signal.aborted) return
    if (payloads.length > 0) {
      phase1Rendered = true
      setResults({ payloads, stats: null, source: 'cache' })
    }
  })

  // Phase 2: merge background scrape results
  scrapePromise.then(result => {
    if (signal.aborted) return

    if (phase1Rendered) {
      // Merge new data into displayed data via pub/sub
      applyBackgroundScrapeResults(result.payloads)
      // Update stats (won't cause article re-render, just stats display)
      setResults(prev => prev ? { ...prev, stats: result.stats } : result)
    } else {
      // No cached data was displayed — render scrape results directly
      setResults(result)
    }

    // Write to sessionStorage
    try {
      sessionStorage.setItem(cacheKey, JSON.stringify({
        timestamp: Date.now(), data: result
      }))
    } catch {}
  }).catch(err => {
    if (err.name === 'AbortError') return
    console.error('Background scrape failed:', err)
    if (!phase1Rendered) {
      setResults({ payloads: [], stats: null })
    }
    // If phase 1 rendered, cached data stays visible — acceptable degradation
  })

  return () => controller.abort()
}, [])
```

## Summary

Two files, ~50 lines of new code, zero server changes. Cached articles display in ~100ms instead of 3-15s. Background scrape merges new articles through the existing pub/sub system. All user state (read, removed, summaries) is preserved across the merge. First-visit and manual-scrape flows are unchanged.
