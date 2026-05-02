---
status: pending
last_updated: 2026-05-02 08:02
---

# Feed Pipeline, Data Flow & Shell

## 1. High — `useFeedLoader` has no request ownership, so stale feed loads can overwrite newer ones

**Why it matters**

`App.jsx` boot load and `ScrapeForm.jsx` both call the same `loadFeed()` entrypoint, but `useFeedLoader` does not track a latest request token and does not cancel or ignore superseded work. If two loads overlap, an older request can still:
1. call `setResults(...)`, or
2. merge stale scrape results into the live cache via `mergeIntoCache(...)`.

That is a correctness bug first, and a UX/perf issue second: the user can briefly or permanently land on the wrong date range after interacting during initial load.

**Evidence**

- `client/src/hooks/useFeedLoader.js:95-135` updates state directly from async work with no request token / latest-request guard.
- `client/src/hooks/useFeedLoader.js:121-126` can still merge an older scrape into cache after a newer request has already started.
- `client/src/App.jsx:236-260` kicks off an initial load on mount.
- `client/src/components/ScrapeForm.jsx:88-103` can start another load from the settings form.
- By contrast, `useSummary` and `useDigest` already use `createRequestToken()` to reject stale async completions (`client/src/hooks/useSummary.js:62-63,90`; `client/src/hooks/useDigest.js:183-189,229-230`).

**Best-practice angle**

This violates the same stale-async-response discipline already used elsewhere in the app. The feed loader should adopt the same “start promise early, commit only if still current” ownership model.

**Recommendation**

Give `useFeedLoader` a `requestTokenRef` (or equivalent latest-request id), and gate every post-await commit (`setResults`, merge, session-cache write, logs if desired) on “is this still the active request?”. Ideally also abort the previous in-flight request when a new one starts.

---

## 2. Medium — app-level storage invalidation forces full shell/feed rerenders on every article mutation

**Why it matters**

The feed already has per-key subscriptions through `useSupabaseStorage`, but `AppContent` also listens to every `supabase-storage-change` event and bumps dummy state just to re-read cache during render. That means a single article-level change can rerender:
1. the whole app shell,
2. the whole feed tree,
3. all selection-derived computations in `AppContent`,

in addition to the targeted subscribers that were already notified.

This is broad invalidation from the top of the tree, exactly where rerenders are most expensive.

**Evidence**

- `client/src/hooks/useSupabaseStorage.js:7-21` emits a global `window` event on every cache change.
- `client/src/App.jsx:53-59` subscribes to that event and increments `setStorageVersion(...)`.
- `client/src/App.jsx:67-89` then re-derives `livePayloads`, `selectedArticles`, and action availability during render.
- `client/src/App.jsx:193` passes the feed back through `<Feed payloads={results.payloads} />`, so the shell-level rerender cascades downward even though `CalendarDay`/article consumers already have finer-grained storage subscriptions.

**Best-practice angle**

This is a classic “subscribe high, rerender wide” pattern. Prefer subscribing as low as possible and deriving only the minimal state each surface needs.

**Recommendation**

Move this cache subscription behind a narrower selector surface instead of invalidating `AppContent` wholesale. Concretely: isolate selection/dock data behind a dedicated storage-backed hook or external-store selector, and keep the feed tree out of that invalidation path.
