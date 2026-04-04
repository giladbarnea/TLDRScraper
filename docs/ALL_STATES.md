---
last_updated: 2026-04-04 18:50
---
# 🔬 State Machine Analysis: Complete Synthesis

## Executive Summary

TLDRScraper’s client-side architecture is orchestrated by **16 distinct state machines** organized into 4 conceptual domains. These machines handle everything from the persistent **Article Lifecycle** to ephemeral **Gesture Recognition** and complex **Multi-article Digests**. The system uses a sophisticated **Zen Lock** mechanism to maintain mutual exclusion between competing full-screen overlays.

---

## Part 1: Individual State Machine Worlds

### Domain A: Article Lifecycle & Interaction

#### 1. Article Lifecycle State Machine
**File:** `client/src/reducers/articleLifecycleReducer.js`

- **States:** `UNREAD` → `READ` → `REMOVED`.
- **Key Logic:** `REMOVED` takes precedence over `READ`.
- **Triggers:** `useArticleState` (hooks), `useSwipeToRemove` (gestures), `useDigest` (batch ops).
- **Effects:** Visual styling (ArticleCard), sorting (ArticleList), and auto-collapse (NewsletterDay).

#### 2. Interaction State Machine
**File:** `client/src/reducers/interactionReducer.js`

- **State:** `{ selectedIds, disabledIds, expandedContainerIds, suppressNextShortPress }`.
- **The Suppression Latch:** Prevents short-press events (like opening a summary) immediately after a long-press (selection).
- **Selection Mode:** Derived as `selectedIds.size > 0`.
- **Interaction with Lifecycle:** Removed articles are registered in `disabledIds` and cannot be selected.

---

### Domain B: Summarization & Data Fetching

#### 3. Summary Data State Machine
**File:** `client/src/reducers/summaryDataReducer.js`

- **States:** `UNKNOWN` → `LOADING` → `AVAILABLE` / `ERROR`.
- **Patterns:** Abort/rollback support using `AbortController` and request token deduplication.
- **Integration:** Shared by both single-article summaries (`useSummary`) and the multi-article digest (`useDigest`).

#### 4. Digest State Machine
**File:** `client/src/hooks/useDigest.js`

- **Lifecycle:** `IDLE` → `TRIGGERING` → `LOADING` → `AVAILABLE` / `ERROR`.
- **Coordination:** Marks ALL participating articles as `LOADING` during generation to provide visual feedback, then restores/updates their state on completion.
- **Persistence:** Digest payloads are stored at the daily payload level (`daily_cache` table).

---

### Domain C: Gestures & Recognition

#### 5. Gesture State Machine (Swipe-to-Remove)
**File:** `client/src/reducers/gestureReducer.js`

- **States:** `IDLE` ↔ `DRAGGING`.
- **Constraint:** `swipeEnabled = canDrag && !isSelectMode`.
- **Visual Feedback:** Trash icon fades in; card translates horizontally.
- **Completion:** slide-off-screen animation → `toggleRemove()` → lifecycle transition.

#### 6. Pull-to-Close & Overscroll Up
**Files:** `client/src/hooks/usePullToClose.js`, `client/src/hooks/useOverscrollUp.js`

- **Pull-to-Close:** Top-boundary (scrollTop=0) pull-down gesture to dismiss overlays (threshold 80px visual).
- **Overscroll-Up:** Bottom-boundary pull-up gesture to mark articles "Done" (threshold 60px/trigger 30px visual).
- **Visuals:** Pull-to-close translates entire overlay; overscroll-up translates content + completion checkmark icon.

---

### Domain D: Storage & View Layer

#### 7. Feed Loading State Machine
**File:** `client/src/App.jsx`

- **States:** `idle` → `fetching` → `cached` → `merged` (or `fetching` → `ready`).
- **Algorithm:** 2-phase load: Phase 1 (instant cache-first render) → Phase 2 (background scrape + merge).
- **Integration:** sessionStorage (10min TTL) → in-memory `readCache` → Supabase.

#### 8. Supabase Storage State Machine (Persistence)
**File:** `client/src/hooks/useSupabaseStorage.js`

- **Pattern:** Optimistic updates with automatic rollback on failure.
- **Module-Level Cache:** `readCache` (L2), `inflightReads` (dedup), `changeListenersByKey` (pub/sub for cross-component sync).
- **Storage Keys:** `newsletters:scrapes:{date}` (article data), `cache:settings:{key}` (UI settings).

#### 9. Scroll Progress State Machine
**File:** `client/src/hooks/useScrollProgress.js`

- **State:** `progress` (0.0 → 1.0).
- **Visual:** ScaleX transform on a thin horizontal bar in overlay headers.
- **Performance:** Uses passive scroll listeners and GPU-accelerated CSS transforms.

#### 10. Toast State Machine
**File:** `client/src/components/ToastContainer.jsx`

- **Lifecycle:** 12s auto-dismiss (11.65s visibility + 350ms exit animation).
- **Pub/Sub:** Triggered via `emitToast()` in `useSummary.js` on successful fetch.
- **Max Visible:** Limits to 2 most recent toasts.

---

## Part 2: Overlay Comparison & Zen Lock

### Digest Overlay vs Zen Mode Overlay

While both overlays share the same **gesture layer** (`useScrollProgress`, `usePullToClose`, `useOverscrollUp`), their behaviors and data integration differ:

| Aspect | ZenModeOverlay (Single Summary) | DigestOverlay (Multi-Article) |
|--------|--------------------------------|-------------------------------|
| **Data Hook** | `useSummary(date, url)` | `useDigest(results)` |
| **Zen Lock Owner** | `article.url` (Unique per article) | `'digest'` (Constant) |
| **Header Identity**| Article Domain + Favicon | Article Count Badge |
| **Mark Removed** | Affects one article | Batch-affects ALL articles |
| **Close Action** | `collapse() → markRead()` | `collapse(true/false) → mark ALL` |

### The Zen Lock Mechanism
**File:** `client/src/hooks/useSummary.js` (Lines 13-22)

The Zen Lock is a **global mutual exclusion lock** that ensures only one full-screen overlay (Summary OR Digest) can be expanded at any time.

1. **Attempt `acquireZenLock(owner)`** before setting `expanded = true`.
2. **Success:** Proceed to expand view.
3. **Failure:** Block expansion (prevents overlapping modals).
4. **`releaseZenLock(owner)`** called on `collapse()` or component unmount.

---

## Part 3: Cross-Machine Interaction Map

| Source Machine | Target Machine | Integration Point | Effect |
|----------------|----------------|-------------------|--------|
| **Article Lifecycle** | Interaction | `registerDisabled(isRemoved)` | Removed articles cannot be selected |
| **Article Lifecycle** | Gesture | `swipeEnabled = !isRemoved` | Disables swipe for removed articles |
| **Article Lifecycle** | Container | `defaultFolded={allRemoved}` | Auto-collapses when all removed |
| **Summary View** | Article Lifecycle | `collapse() → markAsRead()` | Marks article read on close |
| **Summary View** | Zen Lock | `acquireZenLock(url)` | Blocks Digest from opening |
| **Digest** | Article Lifecycle | `markDigestArticlesConsumed()` | Batch marks ALL articles read/removed |
| **Digest** | Summary Data | `markDigestArticlesLoading()` | Sets ALL article summaries to LOADING |
| **Digest** | Zen Lock | `acquireZenLock('digest')` | Blocks Summary from opening |
| **Digest Overlay** | Digest | `onClose → collapse(false)` | Marks articles READ |
| **Digest Overlay** | Digest | `onMarkRemoved → collapse(true)` | Marks articles REMOVED |
| **Gesture** | Article Lifecycle | `onSwipeComplete → toggleRemove()`| Swipe to remove single article |
| **Gesture** | Interaction | `swipeEnabled = !isSelectMode` | Disables swipe during selection |
| **Interaction** | Article Lifecycle | Batch operations | Mark selected read/removed |
| **Overscroll Up** | Article Lifecycle | `onMarkRemoved()` | Marks complete via gesture |
| **Pull To Close** | Overlays | `onClose()` | Dismisses overlay |
| **Supabase Storage** | All | `emitChange()` | Cross-component re-render sync |

---

## Part 4: Key Architectural Patterns

1. **Optimistic Updates with Rollback:** State is updated instantly in `readCache` and React state, with a background task for server persistence and a try/catch block to revert on failure.
2. **Request Token Pattern:** Every async fetch generates a token. Responses are ignored if a newer request (with a newer token) has since started.
3. **Suppression Latch:** A time-based latch (`suppressNextShortPress`) prevents unintended "short press" actions immediately after "long press" events.
4. **Mutual Exclusion (Zen Lock):** Prevents UI collision by managing a single global lock owner for high-level view transitions.
5. **Hierarchical Auto-Collapse:** Parent containers (`CalendarDay`, `NewsletterDay`) derive their fold state from the `removed` status of their children, propagating state changes up the UI tree.
