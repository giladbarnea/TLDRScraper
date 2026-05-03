---
status: pending
last_updated: 2026-05-03 12:38
---

# Plan — Collapsing the Reactive Architecture

## Goal

Replace three coarse reactive buses (per-day storage pub-sub, top-level `window` event, `InteractionContext` mega-value) with one per-article external store. Two outliers (request-token in `useFeedLoader`; render-time markdown) are independent line-items shipped first because they have no architectural blast radius.

## Sequencing

Five steps, each independently shippable. Steps 1, 2, 5 are local fixes. Step 3 is the architectural move and step 4 falls out of it; both can land in the same PR if the diff stays scoped.

---

## Step 1 — Request-token in `useFeedLoader`

**Touches:** `client/src/hooks/useFeedLoader.js`.

The hook accepts an `AbortSignal` for cancellation, but every commit path (`setResults`, `mergeIntoCache`, `writeSessionCachedResults`) runs unconditionally after each await. Add a hook-scoped `requestTokenRef` mirroring `useSummary`/`useDigest`.

<pseudocode>
On entry to `loadFeed`, mint a fresh token, store it in the ref, capture it locally. Before each post-await commit — session-cache short-circuit, phase-one cached render, fresh-payload merge, fresh-payload replace, session-cache write, return value — check the ref still equals the captured token; if not, drop the result silently. Existing `signal.aborted` checks stay and short-circuit before the token check.
</pseudocode>

Do not extract a `useLatestRequest` helper. Three call sites of a five-line shape is below the abstraction threshold.

---

## Step 2 — Markdown rendering at the surface

**Touches:** `client/src/hooks/useSummary.js`, `client/src/hooks/useDigest.js`, `client/src/components/ElaborationPreview.jsx`, `client/src/components/ZenModeOverlay.jsx`, `client/src/components/DigestOverlay.jsx`.

Drop the `html` field from `useSummary` and `useDigest`. The only consumers — `ZenModeOverlay`, `DigestOverlay`, and `ElaborationPreview`'s `AvailableBody` — already render conditionally on visibility. Each consumer derives html from markdown via a memoized derivation keyed on the markdown string.

Strict simplification: hooks return less; markdown work happens only when an overlay is mounted.

---

## Step 3 — Per-article external store

**New module:** `client/src/store/articleStore.js`. Vanilla, no new dependency. Same pub-sub shape as the existing `articleActionBus` and `useSupabaseStorage` — one consistent primitive replacing both.

### Shape

<pseudocode>
The store holds two maps and a small auxiliary slice. The article map is keyed by `${date}::${url}` and each entry holds lifecycle (read object, removed flag, timestamps), summary (status, markdown, errorMessage, effort, expanded view-flag, checkedAt), and a selected boolean. The day map is keyed by date and holds digest, issues, sources metadata, and the day's `storage_updated_at`. The auxiliary slice carries the expanded-container Set and the `suppressNextShortPress` latch already used by the interaction reducer. Listeners are registered per article-key, per date-key, or per global concern (any-selected, expanded-set), and each is notified only when its scoped slice mutates.
</pseudocode>

The store exposes slice subscriptions (`subscribeArticle`, `subscribeDay`, `subscribeContainerExpanded`, `subscribeAnySelected`), each paired with a `getSnapshot`, and actions (`hydrateDay`, `mergeDayFromServer`, `replaceDayFromServer`, `applyArticlePatch`, `applyDayPatch`, plus interaction commands added in step 4). Hooks consume via `useSyncExternalStore`.

### Hooks rewritten on top of the store

<pseudocode>
`useArticleState(date, url)` subscribes to the matching article slice and returns lifecycle plus the lifecycle-event commands, which dispatch through the writer (below) instead of constructing patches inline. `useSummary(date, url)` subscribes to the same slice's summary sub-tree and returns markdown, status, expanded, plus stable command identities (fetch, toggle, collapse, expand) owned by the store. `useDigest(results)` subscribes to a single day-level slice via `targetDate`. None of these hooks recreate their command objects per render.
</pseudocode>

### Hydration

<pseudocode>
`CalendarDay` calls `hydrateDay(payload.date, payload)` once on mount with the payload prop it already receives. The store ingests articles into per-article slices and day-level fields into the day slice. Subsequent re-mounts for the same date route to `mergeDayFromServer`, which preserves optimistic local mutations exactly as `lib/feedMerge.mergePreservingLocalState` does today — same SERVER_ORIGIN_FIELDS list, applied per article slice. The "prop is the authoritative initial value" contract from today's `useSupabaseStorage` is preserved.
</pseudocode>

### Writes and server reconciliation

<pseudocode>
`lib/dailyPayloadMutations.js` keeps its responsibilities — per-key queue, optimistic apply, `expectedUpdatedAt`-gated patch with one 412 retry, rollback on hard failure — but its three touchpoints to in-memory state change. Read latest payload becomes "compose day-slice plus per-article slices from the store". Optimistic apply becomes `applyArticlePatch` or `applyDayPatch`. On success: `replaceDayFromServer(date, patchResult.payload)` so server-authoritative fields win. On rollback: re-fetch the day and `replaceDayFromServer`. The `expectedUpdatedAt` discipline stays because the server's conflict check is still per-row.
</pseudocode>

### Network IO boundary

`hooks/useSupabaseStorage.js` shrinks to a network-only module exposing `loadDailyPayloadFromServer(date)`, `persistDailyPayload(date, payload)`, and the cache-setting variants for non-daily keys. The `useSupabaseStorage` hook, the `readCache` Map, the `window` event, `getCachedStorageValue`, `setStorageValueInMemory`, `mergeIntoCache` are all deleted. The store is the live in-memory surface.

### Coordination kludges that disappear with this step

- `getLivePayload` (`App.jsx:20-24`) and `getLivePayloadForDate` (`useDigest.js:73-76`).
- Every `getCachedStorageValue` read in `App.jsx`, `useDigest.js`, `dailyPayloadMutations.js`.
- `storageVersion` state and `supabase-storage-change` listener in `App.jsx:53-59`.
- `summary`-as-effect-dep in `ArticleCard.jsx:139-154` — commands are stable now, dependency narrows to `[article.url]`.

---

## Step 4 — Collapse `InteractionContext` into the store

**Removes:** `client/src/contexts/InteractionContext.jsx`.

The reducer at `client/src/reducers/interactionReducer.js` stays — its logic (suppress latch, container long-press toggle-all, decision return) is sound. It rebinds onto store state.

<pseudocode>
Selection becomes a `selected` boolean on each article slice. The store maintains a derived `selectedCount` updated alongside slice writes, so `isSelectMode` is a single-listener selector. Container expansion stays as a Set of ids on the auxiliary slice, persisted to localStorage on change with the same key (`expandedContainers:v1`) and JSON shape used today. The interaction reducer's event types map one-to-one onto store actions; the reducer drives each transition pure-functionally over a snapshot of the interaction-relevant slice and the store commits the next slice in one write. The decision-returning event (`itemShortPress`) keeps its synchronous return: action runs reducer over current snapshot, commits, returns the open-or-not decision — no React state on the path.
</pseudocode>

The previous `disabledIds` set is deleted. The reducer instead reads each candidate item's `lifecycle.removed` from the store at decision time. `ArticleCard`'s `registerDisabled` effect goes away.

New hooks: `useIsSelected(id)`, `useIsExpanded(id)`, `useIsSelectMode()`, `useSelectedDescriptors()`. Commands: a single `interactionActions` object with stable references, exported from the store. `Selectable`, `FoldableContainer`, `ArticleCard` switch from `useInteraction()` to these per-id selectors. `Selectable`'s local `useMemo` becomes redundant and is removed.

---

## Step 5 — Date-level batched writes

**Touches:** `client/src/App.jsx` (`applyBatchLifecyclePatch`), `client/src/lib/dailyPayloadMutations.js`, parallel call sites in `client/src/hooks/useDigest.js` (`markDigestArticlesLoading`, `restoreDigestArticlesSummary`, `markDigestArticlesConsumed`).

<pseudocode>
Add a multi-article writer that takes a date and an array of `{url, buildPatch}`. Inside `applyOptimisticPayload` it walks the array once, composes all article-level patches into one updated articles array, and sends one `patchDailyPayload` with the composed payload patch. The batch flips optimistically in a single store broadcast and resolves with one server round trip per date. `applyBatchLifecyclePatch` becomes: group selected articles by date, then one writer call per date. The three `useDigest` loops collapse identically.
</pseudocode>

---

## What we deliberately do not do

1. **No new dependency.** No zustand, immer, jotai. Hand-rolled store using `useSyncExternalStore` — same shape as the codebase's existing pub-subs.
2. **No `useLatestRequest` helper.** Three call sites is below the abstraction threshold.
3. **No multi-store split.** One store with slice subscriptions. Splitting reintroduces coordination, which we just removed.
4. **No `React.memo` sprinkling, no list virtualization, no provider repositioning.** Per-slice subscriptions make ordinary rerender economics sufficient.
5. **No reducer rewrites.** `interactionReducer`, `articleLifecycleReducer`, `summaryDataReducer` stay; the store dispatches to them.
6. **No schema change.** Hydration round-trips byte-for-byte the same payload the server ships and accepts.

---

## Risks and verification

1. **Hydration races.** Two `CalendarDay` mounts for the same date (feed refresh) must route to `mergeDayFromServer`, not overwrite optimistic state. Mitigation: explicit two-entry-point design (`hydrateDay` first, `mergeDayFromServer` thereafter), tracked by a per-date hydration flag in the store.
2. **Selector identity.** Returning new objects from a selector breaks `useSyncExternalStore`'s bail-out. Selectors return slice references and only replace them when contents actually change; consumers either select primitives or use a stable equality check.
3. **localStorage parity for expanded containers.** Verbatim port — same key, same JSON, same write-on-change — preserves user state across the migration.
4. **`mergePreservingLocalState`.** Stays as a pure helper, called by the store's merge action; logic is unchanged.

Per-step manual checks against `builtin cd client && CI=1 npm run dev`:

- **1.** Trigger overlapping `loadFeed` (boot + scrape-form submit pre-boot-resolve); confirm only the latest commits.
- **2.** Open a card with cached summary; in React Profiler, scroll/select and confirm no `markdownToHtml` time.
- **3.** Mark one article read; Profiler shows exactly one `ArticleCard` rerender — no shell, no siblings.
- **4.** Toggle selection on one article; only that `Selectable` rerenders. Toggle a foldable; only that `FoldableContainer` rerenders.
- **5.** Mark N selected articles across two dates as read; DevTools network shows exactly two server round trips and one optimistic flip.
