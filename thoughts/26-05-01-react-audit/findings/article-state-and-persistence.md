---
status: pending
last_updated: 2026-05-02 08:02
---
# Article State & Persistence

Scope note: `client/src/hooks/useLocalStorage.js` is not present in the current tree, so this audit covers the rest of the assigned domain.

## 1. High: one article change re-renders every subscriber for that entire day

**Why it matters**
`ArticleCard` subscribes through `useArticleState()`, which subscribes to `useSupabaseStorage(storageKey, null)`, which stores and broadcasts the **entire daily payload**. On every article mutation, `emitChange(key)` wakes every subscriber for that day, and each `ArticleCard` re-reads the full payload and re-finds its article by URL.

That means a single read/remove/summary change fans out to:
1. every `ArticleCard` for that date,
2. `CalendarDay`,
3. `useDigest` for the active date,
4. `App` as well, via the global `supabase-storage-change` listener.

This is the dominant re-render cost in the domain, and it scales with article count per day rather than with the changed article.

**Evidence**
- `components/ArticleCard.jsx` → `useArticleState(article.issueDate, article.url)`
- `hooks/useArticleState.js` → `useSupabaseStorage(storageKey, null)` then `payload?.articles?.find(...)`
- `hooks/useSupabaseStorage.js` → `emitChange(key)` notifies all listeners for the key
- `components/CalendarDay.jsx` also subscribes to the same key
- `App.jsx` bumps dummy state on every `supabase-storage-change`

**Best-practice angle**
This is a `rerender-*` problem: the store is external/shared, but subscriptions are too coarse. React is doing more work than the UI change requires.

**Suggested direction**
Make this a real external-store boundary with narrower subscriptions:
1. either one day-level subscription high in the tree, passing article state down,
2. or a selector-based store (`useSyncExternalStore` style) so each card subscribes to its own article slice instead of the whole payload.

## 2. Medium: batch lifecycle actions are still an avoidable waterfall

**Why it matters**
Batch actions like “Mark read” / “Mark removed” iterate selected articles and `await queueDailyArticlePatch(...)` **one by one**. Because the optimistic patch is applied inside the queued task, later articles do not even update optimistically until earlier network work finishes.

So for many selected articles on the same date, the UI pays a per-article round trip instead of flipping the whole batch promptly.

**Evidence**
- `App.jsx` → `applyBatchLifecyclePatch()` loops `for (const article of articles) { await queueDailyArticlePatch(...) }`
- `lib/dailyPayloadMutations.js` applies the optimistic update inside `runQueuedOptimisticPatch()` right before `sendPatch(...)`

**Best-practice angle**
This is an `async-*` / waterfall issue more than a pure correctness issue.

**Suggested direction**
Prefer one date-level mutation per batch action, so a whole date’s selected articles update in one optimistic step and one persistence round trip.