---
last_updated: 2026-05-05 06:38, 36614cc
plan: plan.high-level.md
commit: 96f61628
---

# Implementation Notes — React Audit Iteration 1

## What shipped

All five plan steps landed in a single branch (`26-05-01-react-audit`) and one commit (`96f61628`). The two coarse buses that triggered wholesale re-renders on every article write — `useSupabaseStorage`'s in-memory pub-sub and the `window` `supabase-storage-change` event in `App.jsx` — are gone. So is `InteractionContext`, the third broadcast source. `articleActionBus.js` disappeared as a side effect of step 3 (once the store owns summary state, no separate publish channel is needed). `SelectionCounterPill.jsx` was found dead and deleted.

## The `selectedDescriptorsCache` stability problem

The most non-obvious implementation detail. `useSyncExternalStore` bails out of a re-render when the snapshot function returns the same reference as last time. `getSnapshotSelectedDescriptors` returns an array; arrays are never reference-equal unless you cache them. The fix: a module-level `selectedDescriptorsCache` variable replaced by `recomputeSelectedDescriptors()` only when selection actually changes — either inside `applyArticlePatch` when the `selected` field is in the patch, or inside `commitInteractionState` when `selectedCount` shifts. Anything else that calls `getSnapshotSelectedDescriptors` gets the stable cached array back, so components subscribed to `subscribeAnySelected` don't re-render unless the selection truly changed.

## `hydrateDay` vs `mergeDayFromServer` — why two entry points

The store needs to know who stamps `issueDate` on each article slice. That authority belongs to `CalendarDay`, which receives the structural payload prop and knows the date. `hydrateDay` enforces this: it only writes to the store on first mount for a given date; subsequent calls for the same date (triggered by feed refreshes or session-cache replays) are routed to `mergeDayFromServer`, which runs `mergePreservingLocalState` before ingesting. This preserves optimistic mutations the user made between the initial load and the server refresh — exactly the contract `useSupabaseStorage`'s per-key listener enforced before, now expressed as an explicit two-entry-point API on the store.

## `buildOptimistic` closure pattern in the mutation layer

`queueDailyArticlePatch`'s `buildOptimistic` callback captures the `patch`/`buildPatch` variables from its call-site closure. On first evaluation it resolves `buildPatch(latestArticle)` into `resolvedPatch`, then freezes: `patch = resolvedPatch; buildPatch = null`. On the 412-retry path, `buildOptimistic` is called again with the fresh server payload, but the frozen `resolvedPatch` is reused — not recomputed. This is the right behavior: the intent of the user's action was captured at dispatch time, not re-derived from a potentially changed server state. The pattern relies on JavaScript closure mutation, which is why it can't be expressed as a pure function.

## Step 5 drift from plan

The plan specified one server round trip per date for batch writes ("composes all article-level patches into one updated articles array, sends one `patchDailyPayload`"). What was implemented: `queueBatchArticlePatches` groups by date but still calls `queueDailyArticlePatch` per article within each date's serial queue. The call sites (App's `applyBatchLifecyclePatch`, Digest's `updateArticlesAcrossDates`) are cleanly simplified, and dates run in parallel, but articles within a date still each pay a round trip. The single-payload composition would require constructing a diff of the full articles array upfront — feasible, but the added complexity wasn't warranted at this stage given the typical selection size.

## Effects removed from `ArticleCard`

The plan expected `summary` to be narrowed as an effect dependency. In practice both effects — the `registerDisabled` registration and the `subscribeToArticleAction` subscription — were eliminated entirely. `registerDisabled` wasn't needed because `getInteractionSnapshot` derives disabled IDs live from `slice.removed`. The action bus subscription disappeared because callers now dispatch directly to `summaryActions` with an article key, so no per-card listener is needed.

## `interactionActions` as a frozen object

Exported as `Object.freeze({...})` at module evaluation time, the interaction commands are stable references by construction — no `useCallback`, no provider, no per-render identity concern. This is the same pattern used for `summaryActions`. Both objects depend only on module-level Maps and the `interactionReduce` pure function, so they can live at module scope without any React lifecycle coupling.
