---
last_updated: 2026-04-04 19:40
---
# Client State Machines

> A complete map of every state machine in the React client, their individual worlds, and the relations between them.

---

## Table of Contents

- [Part I — The Machines](#part-i--the-machines)
  - [1. Article Lifecycle](#1-article-lifecycle)
  - [2. Summary Data](#2-summary-data)
  - [3. Interaction](#3-interaction)
  - [4. Gesture (Swipe-to-Remove)](#4-gesture-swipe-to-remove)
  - [5. Feed Loading](#5-feed-loading)
  - [6. Digest](#6-digest)
  - [7. Summary View](#7-summary-view)
  - [8. Supabase Storage](#8-supabase-storage)
  - [9. Container Expansion (localStorage)](#9-container-expansion-localstorage)
  - [10. Scrape Form](#10-scrape-form)
  - [11. Zen Mode Overlay](#11-zen-mode-overlay)
  - [12. Digest Overlay](#12-digest-overlay)
  - [13. Scroll Progress](#13-scroll-progress)
  - [14. Pull to Close](#14-pull-to-close)
  - [15. Overscroll Up](#15-overscroll-up)
  - [16. Toast](#16-toast)
- [Part II — The Connective Tissue](#part-ii--the-connective-tissue)
  - [Topology: How They're Wired](#topology-how-theyre-wired)
  - [The Article Object: Shared Substrate](#the-article-object-shared-substrate)
  - [The Three Persistence Tiers](#the-three-persistence-tiers)
  - [Zen Lock: The Mutual-Exclusion Protocol](#zen-lock-the-mutual-exclusion-protocol)
  - [The Two Pub/Sub Buses](#the-two-pubsub-buses)
  - [Coupling Matrix](#coupling-matrix)
  - [Key Cross-Machine Flows](#key-cross-machine-flows)

---

## Part I — The Machines

Each section documents: the state shape, the transitions, who dispatches, who consumes, and what files own it.

---

### 1. Article Lifecycle

| | |
|---|---|
| **Pattern** | Pure reducer function (no `useReducer` — called imperatively) |
| **File** | `reducers/articleLifecycleReducer.js` |
| **Dispatched via** | `hooks/useArticleState.js` → `updateArticle()` → `useSupabaseStorage.setValueAsync()` |

#### States

```
UNREAD  →  READ  →  REMOVED
  ↑          ↑         |
  └──────────┴─────────┘  (RESTORE / TOGGLE_REMOVED)
```

`removed` takes precedence: a removed-and-read article is `REMOVED`.

#### Events

| Event | Transition | Payload |
|---|---|---|
| `MARK_READ` | any → READ (stays REMOVED if removed) | `markedAt` |
| `MARK_UNREAD` | any → UNREAD (stays REMOVED if removed) | — |
| `TOGGLE_READ` | READ ↔ UNREAD | `markedAt` |
| `MARK_REMOVED` | any → REMOVED | — |
| `TOGGLE_REMOVED` | REMOVED ↔ previous | — |
| `RESTORE` | REMOVED → READ or UNREAD | — |

#### Dispatch Sites

| Who | File | When |
|---|---|---|
| `useArticleState` action methods | `hooks/useArticleState.js` | Individual article tap/swipe/overlay-close |
| `applyBatchLifecyclePatch()` | `App.jsx` | Selection dock "Mark Read" / "Mark Removed" |
| `markDigestArticlesConsumed()` | `hooks/useDigest.js` | Digest overlay close |
| `useSummary.collapse()` | `hooks/useSummary.js` | Closing a summary overlay marks article READ |

#### Consumers

| Who | What it reads | Why |
|---|---|---|
| `ArticleCard` | `isRead`, `isRemoved` | Visual styling, conditional rendering, disable selection |
| `ArticleList` | `article.removed` | Sort removed articles to bottom |
| `ReadStatsBadge` | `article.read?.isRead`, `article.removed` | Completion count |
| `CalendarDay`, `NewsletterDay` | `articles.every(a => a.removed)` | Auto-fold when all removed |
| `useSwipeToRemove` | `isRemoved` | Disable drag when removed |
| `InteractionContext` | `isRemoved` via `registerDisabled` | Prevent selecting removed articles |

#### Persistence

State lives on the article object (`removed: bool`, `read: { isRead, markedAt }`) inside the daily payload. Written to Supabase via `useSupabaseStorage` → `POST /api/storage/daily/{date}`.

---

### 2. Summary Data

| | |
|---|---|
| **Pattern** | Pure reducer function (called imperatively, like Article Lifecycle) |
| **File** | `reducers/summaryDataReducer.js` |
| **Dispatched via** | `hooks/useSummary.js`, `hooks/useDigest.js`, `App.jsx` |

#### States

```
UNKNOWN  →  LOADING  →  AVAILABLE
                ↓
              ERROR
                ↓
   ROLLBACK → (previous state)
```

#### Events

| Event | Transition | Payload |
|---|---|---|
| `SUMMARY_REQUESTED` | → LOADING | `effort` |
| `SUMMARY_LOAD_SUCCEEDED` | → AVAILABLE | `markdown`, `effort`, `checkedAt` |
| `SUMMARY_LOAD_FAILED` | → ERROR | `errorMessage` |
| `SUMMARY_RESET` | → UNKNOWN | — |
| `SUMMARY_ROLLBACK` | → whatever `previousData` was | `previousData` |

#### Dispatch Sites

| Who | File | When |
|---|---|---|
| `useSummary.fetchSummary()` | `hooks/useSummary.js` | User taps article → fetch single summary |
| `useSummary` abort handler | `hooks/useSummary.js` | AbortError → ROLLBACK |
| `useDigest.markDigestArticlesLoading()` | `hooks/useDigest.js` | Digest triggered → marks each article LOADING |
| `useDigest` success/error/abort | `hooks/useDigest.js` | Digest response → writes digest-level status |

#### Consumers

| Who | What | Why |
|---|---|---|
| `useSummary` | `status`, `markdown` → `html` | Renders summary overlay content |
| `useDigest` | `status`, `markdown` → `html` | Renders digest overlay content |
| `ArticleCard` | `summary.status`, `summary.isAvailable`, `summary.errorMessage` | Status indicators, error display |
| `App.jsx` | `getSummaryDataStatus()` | Determines which selection actions are available |

#### Persistence

Summary data (`{ status, markdown, effort, checkedAt, errorMessage }`) lives on `article.summary` (or `payload.digest` for digests) inside the daily payload. Same Supabase storage path as Article Lifecycle.

---

### 3. Interaction

| | |
|---|---|
| **Pattern** | `useReducer` + React Context (`InteractionProvider`) |
| **File** | `reducers/interactionReducer.js`, `contexts/InteractionContext.jsx` |
| **Scope** | Global — wraps entire app |

#### State Shape

```js
{
  selectedIds:            Set<string>,   // "article-{url}" or container IDs
  disabledIds:            Set<string>,   // removed articles can't be selected
  expandedContainerIds:   Set<string>,   // "calendar-{date}", "newsletter-…", "section-…"
  suppressNextShortPress: { id, untilMs } // anti-double-fire latch
}
```

Derived: `isSelectMode = selectedIds.size > 0`.

#### Events

| Event | Effect | Dispatched from |
|---|---|---|
| `ITEM_LONG_PRESS` | Toggle item in `selectedIds` + set suppress latch | `Selectable` (article long-press) |
| `CONTAINER_LONG_PRESS` | Toggle all children in `selectedIds` + set suppress latch | `Selectable` (container long-press) |
| `ITEM_SHORT_PRESS` | If suppressed → consume latch. If select mode → toggle selection. Else → return `{ shouldOpenItem: true }` | `Selectable` → `ArticleCard` click handler |
| `CONTAINER_SHORT_PRESS` | If suppressed → consume latch. Else → toggle expand | `FoldableContainer` click |
| `REGISTER_DISABLED` | Add/remove from `disabledIds`; auto-deselect if disabling | `ArticleCard` effect on `isRemoved` change |
| `CLEAR_SELECTION` | Empty `selectedIds` | Selection pill ✕, `App.jsx` after batch ops, `useDigest` after trigger |
| `SET_EXPANDED` | Explicitly set expand state for a container | `FoldableContainer` `defaultFolded` effect |

#### The Suppress Latch

After a long-press, an 800ms window prevents the subsequent touchend's short-press from accidentally toggling expand or opening a summary. Targeted: only suppresses the same ID that was long-pressed.

#### Persistence

`expandedContainerIds` is persisted to `localStorage` under key `expandedContainers:v1` (JSON array). Hydrated on init. `selectedIds` and `disabledIds` are ephemeral.

---

### 4. Gesture (Swipe-to-Remove)

| | |
|---|---|
| **Pattern** | `useReducer` (local to each ArticleCard) |
| **File** | `reducers/gestureReducer.js`, `hooks/useSwipeToRemove.js` |
| **Scope** | Per-article instance |

#### States

```
IDLE  ←→  DRAGGING
 ↑            |
 └─ DRAG_FAILED (errorMessage set, mode back to IDLE)
```

#### Events

| Event | Transition |
|---|---|
| `DRAG_STARTED` | IDLE → DRAGGING |
| `DRAG_FINISHED` | DRAGGING → IDLE |
| `DRAG_FAILED` | DRAGGING → IDLE + errorMessage |
| `CLEAR_ERROR` | Clears errorMessage |

#### Guard Conditions

Swipe is only enabled when: `!isRemoved && !stateLoading && !isSelectMode`. The select-mode guard is applied in `ArticleCard`, not in the reducer.

#### Visual Output

| Phase | Visual |
|---|---|
| Idle | Normal card |
| Dragging | Trash icon fades in behind card |
| Release past threshold (-100px or -300px/s velocity) | Card slides off-screen left, then `toggleRemove()` fires |
| Release before threshold | Card snaps back to x=0 |
| Removed | Grayscale 100%, opacity 0.72 |
| Loading | Grayscale 100%, opacity 0.4 |
| Error | Red error toast via portal, auto-dismiss 5s |

### 5. Feed Loading

| | |
|---|---|
| **Pattern** | `useState` + imperative async flow in `useEffect` |
| **File** | `App.jsx` (top-level `App` component) |
| **Scope** | Singleton — app root |

#### States

```
idle  →  ready                          (session cache hit, < 10 min old)
idle  →  fetching  →  ready             (no cache at all; scrape returns first)
idle  →  fetching  →  cached  →  merged (cache rendered first, then scrape merges in)
```

#### Three-Phase Flow

1. **Session cache check** — `sessionStorage` key `scrapeResults:{start}:{end}`, TTL 10 min. If hit, jump straight to `ready`.
2. **Phase 1 (cache-first)** — `POST /api/storage/daily-range` fetches cached payloads from Supabase. If any exist, render immediately (`cached`).
3. **Phase 2 (background scrape)** — `POST /api/scrape` fetches fresh data. If Phase 1 rendered, merge new articles via `mergeIntoCache()` preserving local state (read/removed/summary). If Phase 1 didn't render, set results directly (`ready`).

#### Merge Algorithm (`mergePreservingLocalState`)

Server-origin fields (`url`, `title`, `articleMeta`, `category`, `sourceId`, `section`, `sectionEmoji`, `sectionOrder`, `newsletterType`, `issueDate`) are overwritten from fresh scrape. Client-state fields (`read`, `removed`, `summary`, `digest`) are preserved from local cache.

#### Error Handling

- `AbortError` → silently ignored (component unmounted).
- Other errors → log, set empty results as fallback.

#### Propagation

```
App (results) → Feed → CalendarDay → NewsletterDay → ArticleList → ArticleCard
```

`CalendarDay` seeds the `readCache` in `useSupabaseStorage` with its payload prop, preventing redundant per-day API calls.

---

### 6. Digest

| | |
|---|---|
| **Pattern** | `useState` + async effects + `summaryDataReducer` for status |
| **File** | `hooks/useDigest.js` |
| **Scope** | Singleton (created in `App.jsx`) |

#### States

```
idle  →  triggering  →  [pending payload load]  →  loading  →  available
                                                       ↓
                                                     error
```

`triggering` is a local boolean; `loading`/`available`/`error` are `summaryDataReducer` states stored on `payload.digest`.

#### Trigger Flow

1. User selects 2+ articles → clicks "Digest" in `SelectionActionDock`.
2. `trigger(articleDescriptors)` checks for cache hit (same URL set → just expand). Otherwise sets `pendingRequest` + `targetDate` + `triggering=true`.
3. A `useEffect` watches for `pendingRequest` + payload loaded → kicks off `runDigest()`.
4. `runDigest()`: marks all participating articles' summaries as LOADING → `POST /api/digest` → on success: restore article summaries, write digest status AVAILABLE, `clearSelection()`, `expand()`.

#### Rollback

On abort or error, `restoreDigestArticlesSummary()` restores each article's `summary` field from a snapshot taken before the request. This undoes the LOADING indicators.

#### Cross-Date Operations

`updateArticlesAcrossDates()` groups article URLs by their `issueDate`, then performs `setStorageValueAsync()` per date. This is necessary because articles in a single digest may span multiple days.

#### Zen Lock

Digest acquires the lock with owner `'digest'` (constant). If a single-article summary is already open, digest expansion is blocked, and vice versa.

---

### 7. Summary View

| | |
|---|---|
| **Pattern** | `useState(false)` for `expanded` boolean + summary data from `summaryDataReducer` |
| **File** | `hooks/useSummary.js` |
| **Scope** | Per-article instance (created in each `ArticleCard`) |

#### Dual State

- **Data state** (persistent): `article.summary.status` — `unknown → loading → available / error`. Managed by `summaryDataReducer`.
- **View state** (ephemeral): `expanded: boolean`. Controls whether the `ZenModeOverlay` portal renders.

#### `toggle(effort)` Decision Tree

```
isAvailable?
  ├─ yes, expanded  → collapse()
  ├─ yes, !expanded → acquireZenLock(url) → setExpanded(true)
  └─ no             → fetchSummary(effort)
```

#### `collapse(markAsReadOnClose = true)`

1. Release zen lock.
2. `setExpanded(false)`.
3. If `markAsReadOnClose && !isRead` → `markAsRead()` (fires Article Lifecycle `MARK_READ`).

#### Abort / Request Token Pattern

- Each `fetchSummary()` call creates a new `AbortController` (aborting any previous) and a unique `requestToken`.
- Stale responses are discarded by comparing `requestTokenRef.current !== requestToken`.
- `AbortError` triggers `SUMMARY_ROLLBACK` to restore previous summary data.

#### Toast Emission

On successful fetch, `emitToast({ title, url, onOpen: expand })` fires. The toast's click handler calls `expand()`, opening the overlay.

---

### 8. Supabase Storage

| | |
|---|---|
| **Pattern** | Custom hook with module-level cache + pub/sub |
| **File** | `hooks/useSupabaseStorage.js` |
| **Scope** | Per-key instance; module-level singletons shared across all instances |

#### Module-Level Singletons

| Singleton | Type | Purpose |
|---|---|---|
| `readCache` | `Map<key, value>` | In-memory cache. Source of truth between renders. |
| `inflightReads` | `Map<key, Promise>` | Request deduplication. Prevents N parallel fetches for the same key. |
| `changeListenersByKey` | `Map<key, Set<fn>>` | Pub/sub. Any `emitChange(key)` notifies all subscribers for that key. |

#### Hook State

```js
const [value, setValue]     = useState(defaultValue)
const [loading, setLoading] = useState(…)
const [error, setError]     = useState(null)
```

#### Optimistic Update (`setValueAsync`)

```
1. Snapshot previous value
2. Optimistic: update React state + readCache + emitChange()
3. Background: writeValue() → POST to server
4. On error: revert React state + readCache + emitChange() + set error
```

#### Key Routing

| Key pattern | Read endpoint | Write endpoint |
|---|---|---|
| `newsletters:scrapes:{date}` | `GET /api/storage/daily/{date}` | `POST /api/storage/daily/{date}` |
| `cache:{setting}` | `GET /api/storage/setting/{key}` | `POST /api/storage/setting/{key}` |

#### Cache Seeding

`CalendarDay` passes the authoritative payload from `/api/scrape` as `defaultValue`. The hook seeds `readCache` if the key is empty, preventing N redundant API calls when ArticleCards mount.

#### Cross-Component Sync

`emitChange(key)` does two things:
1. Calls all registered listeners for that key (same-tab, same-render-tree).
2. Dispatches `window.CustomEvent('supabase-storage-change')` (cross-tab, listened by `App.jsx` to force re-render).

#### Imperative API

`setStorageValueAsync(key, nextValue)` — same optimistic pattern but callable outside React components. Used by `applyBatchLifecyclePatch()` in `App.jsx` and `updateArticlesAcrossDates()` in `useDigest`.

---

### 9. Container Expansion (localStorage)

| | |
|---|---|
| **Pattern** | Part of `InteractionContext` state, persisted to `localStorage` |
| **File** | `contexts/InteractionContext.jsx` |
| **Scope** | Global |

**Note:** `hooks/useLocalStorage.js` exists but is **unused**. All localStorage persistence is handled inside `InteractionContext`.

#### Storage

Single key: `expandedContainers:v1` → JSON array of container IDs.

#### Container ID Patterns

| Pattern | Source | Example |
|---|---|---|
| `calendar-{date}` | `CalendarDay` | `calendar-2024-01-15` |
| `newsletter-{date}-{sourceId}` | `NewsletterDay` | `newsletter-2024-01-15-tldr_tech` |
| `section-{date}-{sourceId}-{sectionKey}` | `NewsletterDay/Section` | `section-2024-01-15-tldr_tech-Web Dev` |

#### Auto-Collapse

`FoldableContainer` accepts `defaultFolded`. When `CalendarDay` or `NewsletterDay` computes `allArticlesRemoved = articles.every(a => a.removed)`, it passes `defaultFolded={true}`, which triggers `setExpanded(id, false)` — removing the ID from `expandedContainerIds` and persisting.

---

### 10. Scrape Form

| | |
|---|---|
| **Pattern** | `useState` + `useActionState` (React 19) |
| **File** | `components/ScrapeForm.jsx` |
| **Scope** | Singleton (in settings panel) |

#### States

```
idle  →  pending  →  success  (onResults called, settings close)
              ↓
            error   (validation or network)
```

#### Validation

- Start ≤ end date.
- Range ≤ 31 days.

#### Simulated Progress

Client-side only: starts at 10%, increments 5% every 500ms capped at 90%, jumps to 100% on success, resets to 0% on error. Does not reflect actual server progress.

#### Integration

`onResults(results)` callback → `App.jsx` sets `results` state + closes settings panel. This bypasses the Feed Loading machine's two-phase flow and directly sets results.

### 11. Zen Mode Overlay

| | |
|---|---|
| **Pattern** | `useState` + three gesture hooks |
| **File** | `components/ArticleCard.jsx` (inner `ZenModeOverlay` component) |
| **Scope** | Per-article, rendered only when `summary.expanded && summary.html` |

#### Own State

`hasScrolled: boolean` — true when `scrollTop > 10`. Drives header visual transition (solid → blurred backdrop).

#### Composed Hooks

| Hook | Role | Output consumed |
|---|---|---|
| `useScrollProgress(scrollRef)` | Reading progress 0→1 | `progress` → thin bar at header bottom |
| `usePullToClose({ containerRef, scrollRef, onClose })` | Pull-down gesture → close overlay | `pullOffset` → `translateY` on entire overlay |
| `useOverscrollUp({ scrollRef, onComplete, threshold: 60 })` | Pull-up at bottom → mark removed | `overscrollOffset`, `isOverscrolling`, `overscrollProgress`, `overscrollComplete` → content shift + green check icon |

#### Close Triggers

| Trigger | Handler | Effect |
|---|---|---|
| ChevronDown button | `onClose()` → `summary.collapse()` | Release lock, mark read |
| Escape key | `onClose()` → `summary.collapse()` | Release lock, mark read |
| Pull-to-close threshold (80px) | `onClose()` → `summary.collapse()` | Release lock, mark read |
| Check button | `onMarkRemoved()` | `summary.collapse(false)` + `markAsRemoved()` |
| Overscroll-up threshold (30px) | `onMarkRemoved()` | `summary.collapse(false)` + `markAsRemoved()` |

---

### 12. Digest Overlay

| | |
|---|---|
| **Pattern** | `useState` + three gesture hooks (identical to Zen Mode) |
| **File** | `components/DigestOverlay.jsx` |
| **Scope** | Singleton, rendered when `digest.expanded` |

#### Own State

`hasScrolled: boolean` — same header blur pattern as Zen Mode.

#### Composed Hooks

Same trio: `useScrollProgress`, `usePullToClose`, `useOverscrollUp`.

#### Differences from Zen Mode

| Aspect | Zen Mode | Digest Overlay |
|---|---|---|
| Content source | Single `article.summary.markdown` | `payload.digest.markdown` (multi-article) |
| Zen lock owner | `article.url` | `'digest'` |
| Header info | Domain + favicon | Article count |
| Mark removed | Single article | All articles in digest |
| Close → mark read | `summary.collapse()` → single article | `digest.collapse(false)` → all articles |
| Check → mark removed | `summary.collapse(false)` + `markAsRemoved()` | `digest.collapse(true)` → all articles |

---

### 13. Scroll Progress

| | |
|---|---|
| **Pattern** | `useState(0)` + passive scroll listener |
| **File** | `hooks/useScrollProgress.js` |
| **Scope** | Per-overlay instance |

#### State

Single float: `progress ∈ [0, 1]`, computed as `scrollTop / (scrollHeight - clientHeight)`.

#### Consumers

Both `ZenModeOverlay` and `DigestOverlay` render a 2px `bg-brand-500` bar at the header bottom, scaled via `transform: scaleX(progress)`.

#### Performance

`{ passive: true }` listener. No throttle needed — browser coalesces scroll events; React 19 batches state updates; the progress bar uses GPU-accelerated CSS transform.

---

### 14. Pull to Close

| | |
|---|---|
| **Pattern** | `useState(0)` + touch event handlers on container ref |
| **File** | `hooks/usePullToClose.js` |
| **Scope** | Per-overlay instance |

#### State

`pullOffset: number` — how many pixels the overlay has been pulled down (with 0.5× damping).

#### Detection

- **Activates** when touch starts outside scroll area OR when `scrollTop === 0`.
- **Pull down** (`diff > 0`): `e.preventDefault()`, set `pullOffset = diff * 0.5`.
- **Pull up** (`diff < -10`): Cancel gesture.
- **Release**: If `pullOffset > 80` (threshold) → `onClose()`. Always reset to 0.

#### Visual

Entire overlay `translateY(pullOffset)`. During pull: no CSS transition (instant tracking). On release: `transition: transform 0.3s ease-out` (spring-back).

#### Boundary Guard

Works in tandem with `useOverscrollUp`. Pull-to-close operates at the **top** boundary; overscroll-up operates at the **bottom** boundary. They never conflict because each checks scroll position before activating.

---

### 15. Overscroll Up

| | |
|---|---|
| **Pattern** | `useState(0)` + touch event handlers on scroll ref |
| **File** | `hooks/useOverscrollUp.js` |
| **Scope** | Per-overlay instance |

#### State

| Value | Type | Derivation |
|---|---|---|
| `overscrollOffset` | number | `min(deltaY * 0.5, threshold * 1.5)` |
| `isOverscrolling` | boolean | `overscrollOffset > 0` |
| `progress` | float 0→1 | `overscrollOffset / (threshold * 0.5)` |
| `isComplete` | boolean | `progress >= 1` |

#### Detection

- **Activates** only when `isAtBottom()` (`scrollHeight - scrollTop - clientHeight < 1`).
- **Pull up** (`deltaY > 0` at bottom): Track offset with 0.5× damping, max `threshold * 1.5`.
- **Release**: If `offset >= threshold * 0.5` (i.e., 30px with default threshold 60) → `onComplete()`. Always reset to 0.

#### Visual Feedback Progression

| Progress | Icon opacity | Icon scale | Background |
|---|---|---|---|
| 0% | 0.3 | 0.8× | `bg-slate-100` |
| 50% | 0.65 | 0.9× | `bg-slate-100` |
| 100% | 1.0 | 1.0× + container 1.1× | `bg-green-500 text-white` |

Content slides up at 0.4× the offset rate during the gesture.

---

### 16. Toast

| | |
|---|---|
| **Pattern** | `useState([])` + pub/sub via `toastBus.js` |
| **File** | `components/ToastContainer.jsx`, `lib/toastBus.js` |
| **Scope** | Singleton (rendered at app root) |

#### State

- **Container**: `toasts: Array<{ id, title, url, onOpen }>`, max 2 (`.slice(-2)`).
- **Per-toast**: `exiting: boolean` (drives exit animation class).

#### Single Trigger Point

Only `useSummary.js` emits toasts — on successful summary fetch:
```
emitToast({ title: article.title, url, onOpen: expand })
```

#### Lifecycle

```
0ms        → Toast appears (animate-toast-in: slide down + fade + scale)
11,650ms   → exiting=true (animate-toast-out: slide up + fade + scale)
12,000ms   → Removed from state
```

Clicking a toast calls `onOpen()` (expands the summary overlay) then dismisses it.

#### Separate Error Toast

`ArticleCard` has a separate inline `ErrorToast` component (red, bottom-positioned, 5s auto-dismiss) for gesture errors. It does **not** use `toastBus` — it's local to the card and driven by `gestureReducer.errorMessage`.

---

## Part II — The Connective Tissue

### Topology: How They're Wired

The 16 machines form a layered architecture. Understanding the layers explains why certain machines know about each other and others don't.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: OVERLAYS (ephemeral view state — portals)                        │
│                                                                             │
│  ┌──────────────────┐   ┌──────────────────┐   ┌────────────────────────┐  │
│  │ Zen Mode Overlay │   │ Digest Overlay   │   │ Toast                  │  │
│  │  ├ ScrollProgress│   │  ├ ScrollProgress│   └────────────────────────┘  │
│  │  ├ PullToClose   │   │  ├ PullToClose   │                              │
│  │  └ OverscrollUp  │   │  └ OverscrollUp  │                              │
│  └──────────────────┘   └──────────────────┘                              │
│            ▲                      ▲                                        │
│            │ zen lock             │ zen lock                               │
│            │ (mutual exclusion)   │                                        │
├────────────┼──────────────────────┼────────────────────────────────────────┤
│  LAYER 3: DOMAIN HOOKS (per-article / per-digest orchestration)            │
│                                                                             │
│  ┌──────────────────┐   ┌──────────────────┐   ┌────────────────────────┐  │
│  │ Summary View     │   │ Digest           │   │ Gesture (Swipe)        │  │
│  │ (useSummary)     │   │ (useDigest)      │   │ (useSwipeToRemove)     │  │
│  └────────┬─────────┘   └────────┬─────────┘   └────────┬───────────────┘  │
│           │                      │                       │                  │
│           │  all three dispatch into ▼                    │                  │
│  ┌────────┴──────────────────────┴───────────────────────┴───────────────┐  │
│  │ useArticleState (per-article facade over reducers + storage)          │  │
│  └────────┬───────────────────────────────────────────────┬──────────────┘  │
│           │                                               │                  │
├───────────┼───────────────────────────────────────────────┼──────────────────┤
│  LAYER 2: PURE REDUCERS (stateless logic — no side effects)                │
│                                                                             │
│  ┌─────────────────────┐   ┌─────────────────────┐                         │
│  │ articleLifecycle     │   │ summaryData         │                         │
│  │ Reducer              │   │ Reducer             │                         │
│  └─────────────────────┘   └─────────────────────┘                         │
│  ┌─────────────────────┐   ┌─────────────────────┐                         │
│  │ interaction          │   │ gesture             │                         │
│  │ Reducer              │   │ Reducer             │                         │
│  └─────────────────────┘   └─────────────────────┘                         │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  LAYER 1: INFRASTRUCTURE (persistence, sync, buses)                        │
│                                                                             │
│  ┌──────────────────────────────┐   ┌───────────────────────────────────┐  │
│  │ Supabase Storage             │   │ Interaction Context               │  │
│  │ (readCache, pub/sub,         │   │ (useReducer + localStorage)       │  │
│  │  optimistic updates)         │   │                                   │  │
│  └──────────────────────────────┘   └───────────────────────────────────┘  │
│  ┌──────────────────────────────┐   ┌───────────────────────────────────┐  │
│  │ articleActionBus             │   │ toastBus                          │  │
│  │ (per-URL pub/sub)            │   │ (global pub/sub)                  │  │
│  └──────────────────────────────┘   └───────────────────────────────────┘  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  LAYER 0: DATA LOADING (app-level orchestration)                           │
│                                                                             │
│  ┌──────────────────────────────┐   ┌───────────────────────────────────┐  │
│  │ Feed Loading                 │   │ Scrape Form                       │  │
│  │ (App.jsx useEffect)          │   │ (useActionState)                  │  │
│  └──────────────────────────────┘   └───────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### The Article Object: Shared Substrate

Most machines don't talk to each other directly. They converge on a **shared data object** — the article — stored inside the daily payload. This is the implicit coupling medium.

```js
{
  // Server-origin (overwritten on scrape merge)
  url, title, articleMeta, issueDate, category,
  sourceId, section, sectionEmoji, sectionOrder, newsletterType,

  // Client-state: Article Lifecycle domain
  removed: boolean,
  read: { isRead: boolean, markedAt: string | null },

  // Client-state: Summary Data domain
  summary: {
    status: 'unknown' | 'loading' | 'available' | 'error',
    markdown: string,
    effort: string,
    checkedAt: string | null,
    errorMessage: string | null,
  },

  // Injected at render time (not persisted)
  originalOrder: number,
}

// Sibling to articles on the payload:
payload.digest: {
  status, markdown, articleUrls, generatedAt, effort, errorMessage
}
```

Article Lifecycle and Summary Data are **two independent domains on the same object**. They never read each other's fields inside their reducers. The coupling happens at the _consumer_ level — e.g., `ArticleCard` reads both `isRemoved` and `summary.status` and decides what to render.

---

### The Three Persistence Tiers

```
┌─────────────────────────────────────────────┐
│  Tier 1: Module-level readCache (Map)       │  ← Instant, same-tab
│  Populated by: cache seeding, API reads,    │
│                optimistic writes             │
├─────────────────────────────────────────────┤
│  Tier 2: sessionStorage                     │  ← Fast, survives re-render
│  Key: scrapeResults:{start}:{end}           │     but not tab close
│  TTL: 10 minutes                            │
├─────────────────────────────────────────────┤
│  Tier 3: Supabase PostgreSQL (daily_cache)  │  ← Durable, cross-device
│  Written via POST /api/storage/daily/{date} │
│  Read via GET /api/storage/daily/{date}     │
└─────────────────────────────────────────────┘
```

Plus a separate `localStorage` tier for `expandedContainerIds` only.

Reads cascade: readCache → (if miss) inflightReads dedup → API → cache + return.
Writes are optimistic: local first → background persist → revert on failure.

---

### Zen Lock: The Mutual-Exclusion Protocol

A module-level variable in `useSummary.js`:

```js
let zenLockOwner = null   // string | null
```

| Operation | Semantics |
|---|---|
| `acquireZenLock(owner)` | If `null`, set to `owner`, return `true`. Else return `false`. |
| `releaseZenLock(owner)` | If `zenLockOwner === owner`, set to `null`. |

**Who acquires:**
- `useSummary.toggle()` / `expand()` → owner = `article.url`
- `useDigest.expand()` → owner = `'digest'`

**Who releases:**
- `useSummary.collapse()` + cleanup effect on unmount
- `useDigest.collapse()` + cleanup effect on unmount

**Effect:** At most one overlay (one Zen Mode OR one Digest) can be expanded at any time. This prevents overlapping portals and ensures the body scroll lock (`document.body.style.overflow = 'hidden'`) is managed by a single owner.

---

### The Two Pub/Sub Buses

#### 1. `toastBus.js`

Global `Set<callback>`. One publisher (`useSummary` on fetch success). One subscriber (`ToastContainer`).

Direction: Summary Data success → Toast notification → (click) → Summary View expand.

#### 2. `articleActionBus.js`

Per-URL `Map<url, Set<callback>>`. Publishers: `App.jsx` selection actions (`publishArticleAction(urls, 'fetch-summary' | 'open-summary')`). Subscriber: `ArticleCard` (via `subscribeToArticleAction`).

Direction: Selection dock action → bridge to per-card summary hooks without prop drilling.

Both buses exist to cross component boundaries that would otherwise require prop drilling through the Feed → CalendarDay → NewsletterDay → ArticleList → ArticleCard hierarchy.

---

### Coupling Matrix

Each cell shows the **direction** of the relationship. Read as "row affects/uses column".

| | Art. Lifecycle | Summary Data | Interaction | Gesture | Feed Loading | Digest | Summary View | Supabase Storage | Overlay Gestures | Toast |
|---|---|---|---|---|---|---|---|---|---|---|
| **Art. Lifecycle** | — | — | Disables selection | — | — | Marks consumed | Marks read on close | Persists via | — | — |
| **Summary Data** | — | — | — | — | — | Shared reducer | Drives overlay content | Persists via | — | Emits toast |
| **Interaction** | Guards selection | Filters actionable | — | Blocks swipe in select mode | — | Clears after trigger | — | — | — | — |
| **Gesture** | Calls toggleRemove | — | Blocked by select mode | — | — | — | — | — | — | — |
| **Feed Loading** | — | — | — | — | — | Provides `results` | — | Reads + merges cache | — | — |
| **Digest** | Marks articles read/removed | Marks articles loading, restores | Clears selection | — | Reads `results.payloads` | — | Shares zen lock | Reads + writes payload | — | — |
| **Summary View** | Marks read on close | Dispatches all events | — | — | — | Shares zen lock | — | Persists via `useArticleState` | — | Emits toast |
| **Supabase Storage** | — | — | — | — | Seeds from payloads | — | — | — | — | — |
| **Overlay Gestures** | `onMarkRemoved` | — | — | — | — | `onMarkRemoved` / `onClose` | `onClose` | — | — | — |
| **Toast** | — | — | — | — | — | — | Click → `expand()` | — | — | — |

---

### Key Cross-Machine Flows

#### Flow 1: User taps an article

```
                            ArticleCard click
                                  │
                    Interaction.ITEM_SHORT_PRESS
                                  │
                   ┌──── suppress latch? ────┐
                   │ yes                     │ no
                   ▼                         ▼
              (consumed,              isSelectMode?
               no-op)           ┌──── yes ────┐── no ──┐
                                ▼              │        ▼
                       toggle selection    decision: shouldOpenItem
                                               │
                                               ▼
                                     summary.toggle(effort)
                                               │
                              ┌──── isAvailable? ────┐
                              │ no                    │ yes
                              ▼                       ▼
                       fetchSummary()        acquireZenLock(url)
                              │                       │
                 Summary Data: REQUESTED        ZenModeOverlay renders
                              │                   (body scroll locked)
                    POST /api/summarize-url
                              │
                 ┌──── success? ────┐
                 │ yes               │ no
                 ▼                   ▼
            LOAD_SUCCEEDED     LOAD_FAILED
            emitToast()        show error
```

#### Flow 2: User swipes an article left

```
                         touch start on card
                                │
               canDrag = !isRemoved && !stateLoading
               swipeEnabled = canDrag && !isSelectMode
                                │
                    ┌──── enabled? ────┐
                    │ no               │ yes
                    ▼                  ▼
                 (no-op)      Gesture: DRAG_STARTED
                              Framer Motion drag active
                                │
                         touch end / release
                                │
                    ┌─── past threshold? ───┐
                    │ no                     │ yes
                    ▼                        ▼
              Gesture: DRAG_FINISHED    animate off-screen
              snap back to x=0          Gesture: DRAG_FINISHED
                                        onSwipeComplete()
                                              │
                                        Art. Lifecycle: TOGGLE_REMOVED
                                              │
                                        Supabase Storage: optimistic write
                                              │
                                        emitChange → all subscribers re-render
                                              │
                                        Interaction: registerDisabled(id, true)
                                        auto-deselect if selected
                                              │
                                        CalendarDay/NewsletterDay:
                                        if allRemoved → auto-fold
```

#### Flow 3: User triggers a digest

```
                    Long-press to select 2+ articles
                                │
                    Interaction: ITEM_LONG_PRESS ×N
                    isSelectMode = true
                                │
                    Click "Digest" in SelectionActionDock
                                │
                    useDigest.trigger(descriptors)
                                │
                    ┌── cache hit (same URLs)? ──┐
                    │ yes                         │ no
                    ▼                             ▼
              expand() immediately          setPendingRequest
              (skip network)               setTriggering(true)
                                                  │
                                           useEffect detects pending + payload ready
                                                  │
                                    markDigestArticlesLoading()
                                    (sets each article.summary → LOADING
                                     saves previous state for rollback)
                                                  │
                                           POST /api/digest
                                                  │
                              ┌──── success? ─────┴──── error/abort ────┐
                              ▼                                         ▼
                    restoreDigestArticlesSummary()         restoreDigestArticlesSummary()
                    writeDigest(AVAILABLE, markdown)       writeDigest(ERROR, msg)
                    clearSelection()
                    acquireZenLock('digest')
                    DigestOverlay renders
                              │
                    User reads digest, then:
                              │
                    ┌── ChevronDown ──┐── Check button/overscroll ──┐
                    ▼                  ▼                              │
              digest.collapse(false)  digest.collapse(true)          │
              mark all READ           mark all REMOVED               │
                    │                  │                              │
                    └──────────┬───────┘                              │
                               ▼                                      │
                    releaseZenLock('digest')                          │
                    setExpanded(false)                                │
```

#### Flow 4: The persistence round-trip

```
   User action (mark read, swipe, summary fetch, etc.)
                        │
            useArticleState.updateArticle(updater)
                        │
            useSupabaseStorage.setValueAsync(fn)
                        │
          ┌─────────────┼─────────────────────┐
          │ OPTIMISTIC   │                     │ BACKGROUND
          ▼              ▼                     ▼
    valueRef.current   readCache.set()    writeValue()
    setValue()         emitChange(key)    POST /api/storage/daily/{date}
    (React re-render)  (subscribers         │
                        re-render)      ┌─── success? ───┐
                                        │ yes             │ no
                                        ▼                 ▼
                                      (done)         REVERT all:
                                                     valueRef = previous
                                                     setValue(previous)
                                                     readCache.set(previous)
                                                     emitChange(key)
                                                     (re-render with old data)
```

#### Flow 5: Feed loading → component tree hydration

```
   App mount
       │
   ┌── sessionStorage hit? ──┐
   │ yes                      │ no
   ▼                          ▼
setResults(cached)     getDailyPayloadsRange() → Phase 1 cached render
                              │
                       scrapeNewsletters() → Phase 2
                              │
                       mergePreservingLocalState()
                       (server fields from scrape,
                        client fields from cache)
                              │
                       mergeIntoCache(key, mergeFn)
                       emitChange(key)
                              │
   App renders Feed
       │
   Feed renders CalendarDay(payload)
       │
   CalendarDay → useSupabaseStorage(key, payload)
       │          ↑ seeds readCache (no API call needed)
       │
   CalendarDay renders NewsletterDay → ArticleList → ArticleCard
       │
   ArticleCard → useArticleState(date, url)
       │           ↑ useSupabaseStorage(key) → cache HIT (seeded by CalendarDay)
       │
   ArticleCard → useSummary(date, url)
       │           ↑ reads article.summary from same payload
       │
   ArticleCard → useSwipeToRemove({ isRemoved, … })
                   ↑ reads isRemoved from useArticleState
```
