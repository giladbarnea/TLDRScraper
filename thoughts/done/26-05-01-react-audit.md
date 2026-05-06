---
status: done
date_completed: 2026-05-06
last_updated: 2026-05-06 07:56
---

# 26-05-01 React Audit & Reactivity Refactor

**The Problem:**
Reactivity was misaligned with the product. The product is per-article, but state was tracked globally and per-day:
- A single article edit (read, remove, toggle) invalidated an entire day's payload via `useSupabaseStorage`.
- A top-of-tree `window` event (`supabase-storage-change`) re-rendered the whole shell and feed on every mutation.
- A mega `InteractionContext` broadcast selection/expansion state across the entire feed.
This caused N-squared rendering costs, a waterfall of single-article network requests for batch actions, and churned effect subscriptions.

**The Solution:**
Collapsed the three coarse reactive buses into a single **per-article external store** (`client/src/store/articleStore.js`) using `useSyncExternalStore`. 

- **Store slices:** Each article holds its own `{ lifecycle, summary, selected }` state.
- **Hydration & Merging:** `hydrateDay` writes initial server payload; `mergeDayFromServer` updates state while strictly preserving optimistic local edits.
- **Targeted Updates:** Listeners subscribe per-article, per-date, or globally (e.g., `isSelectMode`). `Selectable`, `FoldableContainer`, and `ArticleCard` only re-render when their specific ID mutates.
- **Batched Writes:** Replaced per-article waterfall await loops with composed batch patching, pushing an optimistic state flip and sending one server patch per date.
- **Decoupled Heavy Compute:** Moved expensive `markdownToHtml` parsing out of standard hook render paths and deferred it into the visible overlays (`ZenModeOverlay`, `DigestOverlay`, `ElaborationPreview`).
- **Data Flow Fixes:** Added request-token tracking to `useFeedLoader` to stop stale async responses from corrupting the cache.

**Outcome:**
Massively reduced render surface area, decoupled component subscriptions, and stabilized effect closures, resolving UI latency spikes while deleting overarching orchestration kludges (`getLivePayload`, `InteractionContext`).
