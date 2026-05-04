---
status: addressed in 99ce439a
last_updated: 2026-05-04 16:28
---

# Implementation Review — Follow-ups

The architectural skeleton landed. These are the gaps where the plan's *granularity promise* wasn't fully realized, plus one functional regression. Each fix is local; together they finish the work.

## 1. Dock state goes stale during summary fetches on selected articles (regression)

`AppContent` derives `canOpenSingleSummary`, `isSingleSummaryLoading`, and `summarizeEachActionableCount` from non-reactive `getSnapshotArticleByUrl` reads. Its only reactive channels (`useIsSelectMode`, `useSelectedDescriptors`, `useDigest`) don't fire on per-article summary changes. The pre-store `window` event covered this incidentally; the store-based design lost it. Visible symptom: with one article selected, clicking "Summarize" advances the slice through `LOADING → AVAILABLE` but the dock button stays in its pre-fetch state until the next selection change.

<pseudocode>
In `applyArticlePatch`, after writing and notifying the article-keyed listener, also recompute `selectedDescriptorsCache` and fire the any-selected channel whenever the patched slice is currently selected — not only when `selected` itself is the key being patched. Any change to a selected article is a change to the dock-relevant aggregate.
</pseudocode>

## 2. CalendarDay re-renders on every removal toggle in its day

`useDayArticlesSummary` returns a freshly-allocated `{ allRemoved }` object on each snapshot read, so `useSyncExternalStore` cannot bail. And `applyArticlePatch` fires `notifyDay` whenever a patch contains `removed`, regardless of whether `allRemoved` actually flipped. Result: removing one article wakes CalendarDay → NewsletterList → all sibling cards (siblings bail visually but the day-tree work happens).

<pseudocode>
Maintain `{ total, removedCount }` per date in the store, updated incrementally during `ingestPayload` and inside `applyArticlePatch` whenever the patched slice's `removed` flag changes. Cache the derived `{ allRemoved }` object per date and replace it only when `allRemoved` actually flips; fire `notifyDay` only on that flip. `useDayArticlesSummary` then returns the cached reference and CalendarDay re-renders only when the folded-by-default decision can change.
</pseudocode>

## 3. `useIsSelected` is a global subscription, not per-id

Every Selectable subscribes to the any-selected channel; toggling any item wakes every Selectable's snapshot function. The visible result is correct only because the boolean snapshot bails — the architecture itself is not "per-id" as the plan promised.

<pseudocode>
Resolve `id` to an article key through `urlToArticleKey` once and subscribe to that article's listener. Toggling A then wakes only A's Selectable. `useIsSelectMode` and `useSelectedDescriptors` legitimately stay on the any-selected channel.
</pseudocode>

## 4. Per-article round trips inside a date (Step 5 deviation)

`queueBatchArticlePatches` groups by date but still calls `queueDailyArticlePatch` per article inside each date's serial queue. Plan called for one composed `patchDailyPayload` per date.

<pseudocode>
Replace per-article serial dispatch with one composed write per date. Within a single `runQueuedOptimisticPatch` invocation, walk the array of `{url, patch}` once over `latestPayload.articles` to build the next articles array, send one `patchDailyPayload({articles: next})`, and apply each per-article patch to the store in one synchronous loop before the network call so the optimistic UI flips in a single broadcast pass. Existing day-level restore handles rollback.
</pseudocode>

## 5. `useSummary` recreates command closures every render

The hook wraps the stable `summaryActions` in fresh closures (`fetchSummary`, `toggle`, `collapse`, `expand`) on every render. Subscription churn is gone because the bus effect was deleted, but the structural "stable commands" promise isn't kept; future code keying off identity will rediscover the issue.

<pseudocode>
Memoize the returned API by article key — either via `useMemo` keyed on `(date, url)`, or via a module-level cache of frozen objects keyed by article key. The bound methods close only over the key and dispatch to the store's stable `summaryActions`.
</pseudocode>

## 6. Stale slice memory leak in `mergeDayFromServer`

`ingestPayload` adds slices for incoming articles but never removes slices for articles dropped by the merged payload. Repeated refreshes grow the store monotonically.

<pseudocode>
Before re-ingesting a merged day, diff the prior set of keys for that date against the merged payload's articles, and delete stale entries from `articleSlices`, `urlToArticleKey` (only when its current mapping still points at that date), `abortControllers`, `requestTokens`, and `previousSummaryData`. Notify the dropped article listeners last so subscribers observe null and unmount cleanly.
</pseudocode>

## 7. Reducer dead-code

`interactionReducer` still defines `REGISTER_DISABLED` (no dispatcher remains) and threads `state.disabledIds` (which the store rebuilds in `getInteractionSnapshot` on every action — O(N) per click).

<pseudocode>
Drop `disabledIds` from the reducer's state shape and from `getInteractionSnapshot`'s output. Inject an `isDisabled(id)` predicate into the reducer's call context that resolves `id → url → articleKey → slice.removed`. Replace each `state.disabledIds.has(...)` site with the predicate. Delete the `REGISTER_DISABLED` event type and case.
</pseudocode>

## Out of scope

- `composePayloadFromStore`'s O(total) walk-and-filter is per-mutation, not per-render. Skip until profiles show cost.
- The `article`-prop-vs-store-slice dual source is fine while only server-origin fields flow through props. Do not introduce indirection until something mutates server-origin fields client-side.
- StrictMode-induced double-hydrate firing per-article notifications is dev-only and harmless.
