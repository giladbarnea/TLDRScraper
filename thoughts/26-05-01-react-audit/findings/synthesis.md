---
status: pending
last_updated: 2026-05-03 15:10, bb6b54a
---

# Synthesis — React Audit

## 1. The four findings are the same finding seen from four angles

All four reports flag the same structural seam: **cross-cutting reactive state is plumbed through React's render cycle at the wrong granularity.** The product is per-article, but the runtime is per-day-payload-and-shell.

There are three coarse buses doing this, each amplifying the others:

1. **Per-day storage pub-sub** in `hooks/useSupabaseStorage.js`. One subscription = one whole-day payload. Every article-level change `emitChange(key)`s the entire day to every subscriber — every `ArticleCard` for that date, `CalendarDay`, `useDigest`. Each subscriber re-reads the full payload and re-derives its slice. (Finding 1.1.)
2. **Top-of-tree invalidation** in `App.jsx:53-59`. `AppContent` listens to the global `window` event `supabase-storage-change` and bumps `storageVersion`. Any article mutation → whole shell rerender → whole `<Feed>` tree rerender → every `useArticleState` and `useSummary` re-run, *on top of* their own per-day subscriptions firing. (Finding 2.2.)
3. **Mega-context** in `contexts/InteractionContext.jsx`. One context value carries `selectedIds`, `expandedContainerIds`, `isSelectMode`, plus state-dependent callbacks (`itemShortPress` rebuilds when `state` changes via `dispatchWithDecision`'s `[state]` dep). Every selection toggle, every expand/collapse, every short-press latch update reissues the value object → all consumers across the feed rerender. (Finding 4.1.)

The two "Medium" findings are downstream symptoms of the above:

- Finding 3.2 / 4.2 (`useSummary` returns unstable commands → `ArticleCard` bus subscription churn). This *only* hurts because finding 4.1 is already firing broad rerenders across cards. With narrower subscriptions, this churn stops happening; without narrower subscriptions, even stabilizing `useSummary` only patches one symptom.
- Finding 1.2 (per-article await waterfall in `applyBatchLifecyclePatch`, `App.jsx:31-48`). It's a waterfall because each iteration uses the per-article writer `queueDailyArticlePatch` instead of one date-level write — i.e., the writer side mirrors the reader side's wrong granularity.

Two outliers are real but localized:

- Finding 2.1 (`useFeedLoader` has no request-token guard). Pure async-ownership bug. The codebase already has the helper (`createRequestToken()` in `lib/requestUtils.js`) and the pattern is used in `useSummary`, `useDigest`. Just apply it.
- Finding 3.1 (`markdownToHtml()` runs in every `useSummary`/`useDigest`/`ElaborationPreview` render, including invisible cards). The hook computes HTML in `useSummary.js:22` and `useDigest.js:45` regardless of `expanded`. `ElaborationPreview` recomputes inside `AvailableBody` on each render. Pure work-in-the-wrong-place.

## 2. Why these patterns are coupled in a way the individual reports don't fully expose

Look at the cascade for a single article `read` toggle today:

1. `useArticleState.markAsRead()` → `queueDailyArticlePatch` → `setStorageValueInMemory(storageKey, …)` → `emitChange(key)`.
2. **Per-day listeners fire** — every `ArticleCard` on that day re-reads payload, runs `articles.find(...)`, re-renders. (1.1)
3. **`window` event fires** — `AppContent` bumps `storageVersion`, re-renders, recomputes `livePayloads`, `selectedArticles`, etc., then re-renders `<Feed payloads={results.payloads} />` with a stable prop but a new render pass. (2.2)
4. Inside that pass each `ArticleCard` runs `useSummary(...)` which **returns a fresh object** (3.2). The card's `useEffect(..., [..., summary])` tears down and re-attaches the `subscribeToArticleAction` subscription. (4.2)
5. `useSummary` also calls `markdownToHtml(markdown)` for any card that already has cached summary markdown — even if the overlay is closed. (3.1)
6. If selection state is involved, `InteractionContext`'s `value` object gets a fresh identity on every reducer step, so all `Selectable`s, `FoldableContainer`s, `ArticleCard`s rerender independently of the storage path. (4.1)

A single toggle therefore traverses three independent broadcast mechanisms — and the work *inside* each rerender (markdown parsing, full-payload `find`, full selection walk via `getSelectedArticles`) is itself O(articles per day) or worse.

## 3. The one move that collapses all of this: per-article slices behind a single external store

The codebase already has the shape it needs to converge on; it just hasn't done so:

1. `lib/articleActionBus.js` is already a per-URL pub/sub. Mirror its keying for **state**, not just commands. One subscription per article.
2. `lib/dailyPayloadMutations.js` already centralizes optimistic-write + queue + 412 retry. It's the right writer; just point it at per-URL slices instead of broadcasting whole payloads to subscribers.
3. `useSupabaseStorage`'s `readCache` Map is already a process-wide cache. Treat it as **server hydration**, not as the reactive surface.

Concretely: introduce one external store keyed by `articleKey = ${date}::${url}`, exposing slice subscriptions via `useSyncExternalStore` (or zustand — same shape). The store holds:

- `lifecycle` (`read`, `removed`, timestamps)
- `summary` (`status`, `markdown`, `errorMessage`, `effort`, `expanded` — yes, `expanded` belongs here, it's per-article UI state)
- a small `selection` slice (one boolean per article) and per-container `expanded` flag, replacing `InteractionContext`'s sets

Hydration happens once when `CalendarDay` mounts with a payload (the path already exists; today it seeds `readCache` directly). Mutations write through `queueDailyPayloadPatch` to the server and update only the affected slices; subscribers for unaffected slices are untouched.

This is one architectural change but it cleanly subsumes findings 1.1, 2.2, 3.2, 4.1, 4.2:

| Finding | What changes |
|---|---|
| 1.1 — coarse per-day fan-out | Card subscribes to its slice. Toggling article A doesn't notify article B. |
| 2.2 — `window` event invalidates whole shell | The global event goes away. `AppContent` reads selection from a *selector* of the store; it rerenders only when that selector's output changes. |
| 3.2 / 4.2 — unstable `useSummary` → bus churn | Commands become stable store actions, not closures over render state. The `subscribeToArticleAction` effect's dependencies become `[article.url]` only. |
| 4.1 — `InteractionContext` mega-value | Selection lives in the store as per-article booleans plus a small derived `isSelectMode`. `Selectable` subscribes to "am I selected"; toggling A doesn't rerender B. `FoldableContainer` subscribes to "am I expanded". |
| 1.2 — per-article await waterfall | `applyBatchLifecyclePatch` becomes one `queueDailyPayloadPatch` per date for N articles: one optimistic apply, one network round trip, one re-broadcast — but only to the slices that changed. |

The two outliers are independent line-items that fall out cleanly:

- Finding 2.1 — `useFeedLoader` adopts `requestTokenRef` like `useSummary`/`useDigest`. The helper exists; one ref + one guard before each `setResults`/`mergeIntoCache` commit.
- Finding 3.1 — move `markdownToHtml` out of `useSummary`/`useDigest`/`ElaborationPreview`'s `AvailableBody` render. `ZenModeOverlay`, `DigestOverlay`, and the `available` body of `ElaborationPreview` are the only consumers; let them compute it under `useMemo([markdown])`. With per-slice subscriptions, this also means a card with cached summary markdown doesn't pay any markdown cost while collapsed.

## 4. Why this is a product-fit move, not a perf hack

The product unit is the article. Lifecycle is per-article. Summary is per-article. Selection is per-article. Read state is per-article. The day payload exists for one reason: it's how the server stores and ships data. Today the UI reactivity inherits the *server's storage shape* instead of the *product's interaction shape*. Aligning reactivity with the product unit:

1. **Reads what changed.** A reader marking one article read causes one slice broadcast and one card rerender.
2. **Writes what changed.** A batch mark-read causes one optimistic apply and one server round trip per affected date, regardless of N articles per date.
3. **Eliminates two whole subsystems** (the global `window` event, the `InteractionContext` mega-value with its `dispatchWithDecision` `[state]` rebuild) by collapsing them into the article slice.
4. **Removes coordination kludges.** `getLivePayload` (`App.jsx:20-24`), `getLivePayloadForDate` (`useDigest.js:73-76`), and the `getCachedStorageValue` reads scattered through `App.jsx`, `useDigest.js`, `dailyPayloadMutations.js` exist because today's reactive surface (the per-day subscription) doesn't expose live article state directly. Once the store is the live surface, those helpers go away.
5. **Lets `useFeedLoader`'s job shrink to "fetch payloads, hydrate the store"** — it's no longer the source of truth for article state during render; it's just the IO boundary.

## 5. Suggested order of operations (each step independently shippable)

1. **Request-token in `useFeedLoader`** (Finding 2.1). Smallest, safest, no architecture impact. Promotes the `createRequestToken` pattern to a `useLatestRequest` helper if a third caller emerges.
2. **Move `markdownToHtml` to overlay surfaces** (Finding 3.1). Strictly local change to `useSummary.js:22`, `useDigest.js:45`, `ElaborationPreview.jsx:55`. Memoize at consumer with `useMemo([markdown])`.
3. **Introduce the per-article store** (slice = `{ lifecycle, summary, expandedView }`). Hydrate from `payload.articles` on `CalendarDay` mount; keep `dailyPayloadMutations` as the writer but have it call store actions instead of `setStorageValueInMemory(storageKey, …)`. Have `useArticleState`/`useSummary` read from the store.
   At this point findings 1.1, 3.2, 4.2 close. The `window` event in `App.jsx:53-59` becomes dead code and is removed (closes 2.2).
4. **Move selection + expansion into the store**. `Selectable` and `FoldableContainer` switch from `useInteraction()` to per-id selectors. `InteractionContext` either shrinks to commands only or disappears (the reducer logic stays — it's good — it just becomes the store's reducer). Closes 4.1.
5. **Date-level batched writes** (Finding 1.2). Replace the loop in `applyBatchLifecyclePatch` with one `queueDailyPayloadPatch` per date computing all article patches in `applyOptimisticPayload`.

Steps 1, 2, and 5 are isolated wins even without step 3-4. But step 3-4 is where the architecture gets meaningfully simpler — fewer subsystems, fewer coordination paths, less render-time work everywhere — rather than just faster.

## 6. What disappears, in concrete terms

- The `window.dispatchEvent('supabase-storage-change')` path in `useSupabaseStorage.js:19-21`.
- The `storageVersion` state and its subscription in `App.jsx:53-59`.
- `getLivePayload` (`App.jsx:20-24`) and `getLivePayloadForDate` (`useDigest.js:73-76`).
- The `getCachedStorageValue` reads scattered across `AppContent`, `useDigest`, `dailyPayloadMutations` — the store is the live surface now.
- The `[state]` dep on `dispatchWithDecision` in `InteractionContext.jsx:55-59` and the resulting whole-context-rebuild on every event.
- Per-card `summary`-as-effect-dep in `ArticleCard.jsx:139-154`.
- Render-time `markdownToHtml` calls for invisible cards.
- The per-article await loop in `App.jsx:37-46`.

The net direction: fewer mechanisms, each doing exactly one job at the granularity the product actually has.
