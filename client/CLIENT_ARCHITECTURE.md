---
name: client architecture
description: Client-side architecture for the Newsletter Aggregator
last_updated: 2026-02-06 11:43, 6fd30cd
---
# Client Architecture


## Overview

This document maps the frontend architecture of the Newsletter Aggregator. It details:
- **System Boundaries**: How the React client interacts with the backend API.
- **Rendering Hierarchy**: The component tree structure and dependencies.
- **Interaction Flow**: The chronological steps of user actions (Scraping, Reading, Archiving).
- **Data Transformation**: How raw API payloads are enriched with user state and persisted.

---

The client is built as a Single Page Application (SPA) using React and Vite. It relies heavily on an Optimistic UI pattern where local state updates immediately for the user while syncing asynchronously to the backend via useSupabaseStorage. The architecture uses cache-first hydration: on mount, cached payloads are fetched from `/api/storage/daily-range` and rendered immediately, then `/api/scrape` runs in the background and merges new articles into the live display via `mergeIntoCache`. CalendarDay seeds the storage cache with the payload it receives on mount—eliminating redundant per-day storage fetches while preserving pub/sub reactivity for state changes. The architecture emphasizes "Zen Mode" reading, dividing the view into a Feed (browsing) and an Overlay (reading).

## Architecture Diagram

> Focus: Structural boundaries, State management, and External relationships.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER / CLIENT                                                       │
│                                                                         │
│  ┌──────────────┐    ┌───────────────────────────────────────────────┐  │
│  │     USER     │───►│             APP CONTAINER (Main)              │  │
│  │ (Interacts)  │    │  ┌────────────┐ ┌──────────┐ ┌─────────────┐  │  │
│  └──────────────┘    │  │ ScrapeForm │ │ Header   │ │ Feed Layout │  │  │
│                      │  └─────┬──────┘ └────┬─────┘ └──────┬──────┘  │  │
│                      └────────│─────────────│──────────────│─────────┘  │
│                               │             │              │            │
│  ┌────────────────────────────▼─────────────▼──────────────▼─────────┐  │
│  │                       COMPONENT HIERARCHY                         │  │
│  │  ┌──────────────┐   ┌─────────────────┐    ┌───────────────────┐  │  │
│  │  │ CalendarDay  │──►│ NewsletterDay   │───►│ ArticleCard       │  │  │
│  │  └──────────────┘   └─────────────────┘    └────────┬──────────┘  │  │
│  │                                                     ▼             │  │
│  │                                            ┌───────────────────┐  │  │
│  │                                            │ ZenModeOverlay    │  │  │
│  │                                            └───────────────────┘  │  │
│  └─────────────────────────────────────────────────────────┬─────────┘  │
│                                                            │            │
│  ┌─────────────────────────────────────────────────────────▼─────────┐  │
│  │                       STATE & SYNC LAYER                          │  │
│  │  ┌──────────────────┐  ┌───────────────────┐  ┌────────────────┐  │  │
│  │  │ useSupabaseStore │  │ useArticleState   │  │ useSummary     │  │  │
│  │  └────────┬─────────┘  └─────────┬─────────┘  └──────┬─────────┘  │  │
│  └───────────│──────────────────────│───────────────────│────────────┘  │
╞══════════════│══════════════════════│═══════════════════│═══════════════╡
│  BACKEND API ▼                      ▼                   ▼               │
│         ┌──────────┐          ┌──────────┐        ┌───────────┐         │
│         │ /scrape  │          │ /storage │        │ /summarize-url │         │
│         └──────────┘          └──────────┘        └───────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Selection and Interaction Architecture

### Goals

Selection behavior is implemented as a **declarative state machine** with a small set of events. The implementation goals are:
- Make selection mode deterministic and easy to reason about.
- Keep container expand/collapse **orthogonal** to selection.
- Ensure long-press never accidentally triggers the short-press behavior ("double fire").

### Key modules
- `contexts/InteractionContext.jsx`
  - Provides `useInteraction()`: UI-facing functions (short press / long press) and selectors (isSelectMode, isSelected, isExpanded).
- `reducers/interactionReducer.js`
  - The single source of truth for transitions.
  - Implements suppression of the short press immediately following a long press on the same target.
- `hooks/useLongPress.js`
  - Pointer-event long press detection for mobile and desktop.

### Component responsibilities
- **Selectable**
  - Detects long press and dispatches LONG_PRESS events to the interaction layer.
  - Renders selection checkmark for items (and can be extended for container UI states if desired).
- **ArticleCard**
  - On click, calls `itemShortPress(articleId)`:
    - In Normal mode: returns "should open" → opens TLDR/Zen overlay.
    - In Select mode: toggles selection (no open).
- **FoldableContainer**
  - On click, calls `containerShortPress(containerId)` to expand/collapse, regardless of selection mode.

---

## Interaction State Machine Prose

### Normal mode

#### Short press

**Item**
- **Action:** `openItem(itemId)` (navigate to full-screen item view / open overlay)
- **Selection:** no change
- **Mode:** stays Normal

**Container**
- **Action:** `toggleExpand(containerId)` (expand ↔ collapse)
- **Selection:** no change
- **Mode:** stays Normal
- **Note:** expand/collapse is orthogonal to selection (still works in Select mode too)

#### Long press

**Item**
- **Action:** `toggleSelect(itemId)`
- **Mode rule:** if selection becomes non-empty → enter Select; if empty → remain/return to Normal
- **UI:** checkmark appears; selection counter appears if selection non-empty

**Container**
- **Action:** `toggleSelectAllChildren(containerId)`
  - If all children currently selected → deselect them all
  - Else → select them all
- **Mode rule:** same as above (non-empty selection ⇒ Select, empty ⇒ Normal
- **UI:** checkmarks apply to affected children; counter updates

---

### Select mode

#### Short press

**Item**
- **Action:** `toggleSelect(itemId)` (same effect as long press on an item)
- **Mode rule:** if selection becomes empty → exit to Normal; else stay Select

**Container**
- **Action:** `toggleExpand(containerId)` (same as in Normal)
- **Selection:** no change
- **Mode:** stays Select (unless something else empties selection)

#### Long press

**Item**
- **Action:** `toggleSelect(itemId)` (identical to short press in Select mode)

**Container**
- **Action:** `toggleSelectAllChildren(containerId)` (identical to long press in Normal mode)

---

## Interaction Reducer Pseudocode

The reducer is the canonical definition of behavior. The app dispatches only these events:
- `ITEM_SHORT_PRESS(itemId)`
- `ITEM_LONG_PRESS(itemId)`
- `CONTAINER_SHORT_PRESS(containerId)`
- `CONTAINER_LONG_PRESS(containerId, childIds)`
- `CLEAR_SELECTION`
- `REGISTER_DISABLED(id, isDisabled)`

Pseudocode (intentionally not language syntax):

1. **Derived mode:**
   - `mode = (selectedIds is empty) ? Normal : Select`

2. **Long press rules (always selection-related):**
   - On `ITEM_LONG_PRESS(itemId)`:
     - Toggle `itemId` in `selectedIds`
     - Latch: "suppress the next SHORT_PRESS for this same itemId"
   - On `CONTAINER_LONG_PRESS(containerId, childIds)`:
     - If all selectable childIds are selected:
       - Remove all those childIds from `selectedIds`
     - Else:
       - Add all selectable childIds to `selectedIds`
     - Latch: "suppress the next SHORT_PRESS for this same containerId"

3. **Short press rules:**
   - On `CONTAINER_SHORT_PRESS(containerId)`:
     - If suppression latch matches containerId, consume latch and do nothing
     - Else toggle expand/collapse for containerId
     - (Selection does not change)
   - On `ITEM_SHORT_PRESS(itemId)`:
     - If suppression latch matches itemId, consume latch and do nothing
     - Else if mode == Select:
       - Toggle `itemId` in `selectedIds`
     - Else (mode == Normal):
       - Do not mutate selection; return a decision "shouldOpenItem = true"

4. **Disabled IDs:**
   - On `REGISTER_DISABLED(id, isDisabled)`:
     - Maintain a `disabledIds` set
     - If something becomes disabled, ensure it is not selected

5. **Clearing selection:**
   - On `CLEAR_SELECTION`:
     - Clear `selectedIds` (therefore exiting select mode)

---

## Article Lifecycle State Machine (Domain A)

### Overview
Article lifecycle management (`unread` → `read` → `removed`) is implemented as a **closed reducer** pattern following the guidance in `thoughts/26-01-30-migrate-to-reducer-pattern/`.

### Key modules
- `reducers/articleLifecycleReducer.js`
  - Single source of truth for lifecycle state transitions
  - Exports `ArticleLifecycleState` enum: `UNREAD`, `READ`, `REMOVED`
  - Exports `ArticleLifecycleEventType` enum: `MARK_READ`, `MARK_UNREAD`, `TOGGLE_READ`, `MARK_REMOVED`, `TOGGLE_REMOVED`, `RESTORE`
  - Pure reducer function: `reduceArticleLifecycle(article, event)` returns `{ state, patch }`
- `hooks/useArticleState.js`
  - Provides UI-facing functions (`markAsRead`, `markAsUnread`, `toggleRead`, `markAsRemoved`, `toggleRemove`)
  - All functions dispatch events to the lifecycle reducer
  - Integrates transition logging automatically
  - Returns computed `lifecycleState` for consumers

### Event-driven pattern
Components dispatch **events** (declarative intent) rather than calling setters (imperative commands):
```javascript
// UI calls this:
markAsRead()

// Internally dispatches:
dispatchLifecycleEvent({
  type: ArticleLifecycleEventType.MARK_READ,
  markedAt: new Date().toISOString()
})

// Reducer computes next state and storage patch:
{ state: 'read', patch: { read: { isRead: true, markedAt: '...' } } }
```

### Storage integration
The reducer is **closed** (no side effects, no cross-domain reads). It returns a storage `patch` that describes the minimal update. The patch is applied via the existing `updateArticle` mechanism, which syncs to Supabase storage through `useSupabaseStorage`.

### Transition logging
State transitions are logged automatically in `dispatchLifecycleEvent`. Only actual state changes are logged (no redundant logs for no-ops like marking an already-read article as read).

---

## Summary State Management (Domain B + Simple View State)

### Overview
Summary management uses **a reducer for complex data** (Domain B) and **simple state for UI** following React best practices:

- **Domain B (Data)**: What summary data we have (`unknown` → `loading` → `available`/`error`) - **Reducer pattern**
- **View State**: How the summary is displayed (collapsed ↔ expanded) - **Simple `useState(boolean)`**

The `useSummary` hook orchestrates the data reducer and manages view state directly.

### Key modules

**Domain B: Summary Data Reducer**
- `reducers/summaryDataReducer.js`
  - Exports `SummaryDataStatus` enum: `UNKNOWN`, `LOADING`, `AVAILABLE`, `ERROR`
  - Exports `SummaryDataEventType` enum: `SUMMARY_REQUESTED`, `SUMMARY_LOAD_SUCCEEDED`, `SUMMARY_LOAD_FAILED`, `SUMMARY_ROLLBACK`
  - Pure reducer: `reduceSummaryData(summaryData, event)` returns `{ state, patch }`
  - Getter: `getSummaryDataStatus(summaryData)` derives current status

**Orchestrator**
- `hooks/useSummary.js`
  - Provides UI-facing functions (`fetch`, `toggle`, `expand`, `collapse`)
  - Dispatches to data reducer: `dispatchSummaryEvent(event)` → data transitions (persisted)
  - Manages view state: `useState(expanded)` → simple boolean for UI visibility
  - Coordinates: successful data load → auto-expand view (if zen lock acquired)
  - Manages side effects: API fetch, zen lock, mark as read, request tokens

### Coordination examples

**User clicks "Summary" button (data not available):**
```javascript
// UI calls:
toggle()

// Dispatches to data reducer:
dispatchSummaryEvent({
  type: SummaryDataEventType.SUMMARY_REQUESTED,
  effort: 'low'
})

// On success, dispatches to data reducer:
dispatchSummaryEvent({
  type: SummaryDataEventType.SUMMARY_LOAD_SUCCEEDED,
  markdown: result.summary_markdown,
  effort: 'low',
  checkedAt: new Date().toISOString()
})

// Then updates view state (if zen lock acquired):
if (acquireZenLock(url)) {
  logTransition('summary-view', url, 'collapsed', 'expanded', 'summary-loaded')
  setExpanded(true)
}
```

**User clicks when summary available (toggle visibility):**
```javascript
// UI calls:
toggle()

// Simply toggles view state:
if (expanded) {
  collapse() // calls setExpanded(false) + releaseZenLock()
} else if (acquireZenLock(url)) {
  logTransition('summary-view', url, 'collapsed', 'expanded', 'tap')
  setExpanded(true)
}
```

### Storage integration

**Domain B (data)** is persisted to Supabase:
- Reducer returns storage `patch` describing minimal update
- Applied via `updateArticle` → syncs through `useSupabaseStorage`
- Persisted fields: `status`, `markdown`, `effort`, `checkedAt`, `errorMessage`

**View state** is component-local:
- Not persisted (ephemeral UI state)
- Simple `useState(expanded)` boolean in `useSummary` hook
- Reset on component unmount

### Request token pattern

Domain B implements request tokens to prevent stale updates:
```javascript
const requestToken = createRequestToken()
requestTokenRef.current = requestToken

// Later, when response arrives:
if (requestTokenRef.current !== requestToken) return  // Ignore stale response
```

This ensures rapid tap-abort-tap sequences don't corrupt state with out-of-order responses.

### Rollback on abort

When a fetch is aborted, Domain B rolls back to previous state:
```javascript
if (error.name === 'AbortError') {
  dispatchSummaryEvent({
    type: SummaryDataEventType.SUMMARY_ROLLBACK,
    previousData: previousSummaryDataRef.current
  })
}
```

This prevents cached summaries from being stuck in perpetual loading state.

### Transition logging

Both data and view transitions are logged automatically:
- Domain B: Logs data state changes (`unknown` → `loading` → `available`)
- View state: Logs expand/collapse with reason (`tap`, `summary-loaded`)
- Only actual state transitions are logged (no redundant logs)

### Design rationale

**Why a reducer for Domain B?**
- Complex async state machine with multiple events and invariants
- Rollback-on-abort requires careful state management
- Request tokens need coordination with transitions
- Benefits from the guarantees a reducer provides

**Why simple useState for view?**
- It's a boolean toggle (collapsed ↔ expanded)
- No complex invariants or business logic
- Ephemeral UI state (doesn't persist)
- Using a reducer would be over-engineering

**Why not a view reducer?**
- Violates "simplest thing that works" principle
- Adds ~40 lines of code for a one-line useState
- No proportional benefit to the added complexity
- Inconsistent with React idioms (useState for simple state)

**Why request tokens instead of persisting them?**
- Tokens are transient runtime state with no user value
- Would pollute cached data in Supabase
- Component-local refs are sufficient for preventing stale updates

---

## Gesture Interaction State Management (Domain D)

### Overview
Swipe-to-remove gesture state (`idle` → `dragging` with error handling) is implemented as a **closed reducer** pattern following the migration effort documented in `thoughts/done/26-01-30-migrate-to-reducer-pattern.md`.

### Key modules
- `reducers/gestureReducer.js`
  - Single source of truth for gesture drag state transitions
  - Exports `GestureState` enum: `IDLE`, `DRAGGING`, `ERROR`
  - Exports `GestureEventType` enum: `DRAG_STARTED`, `DRAG_FINISHED`, `DRAG_FAILED`, `CLEAR_ERROR`
  - Pure reducer function: `reduceGesture(state, event)` returns new state
- `hooks/useSwipeToRemove.js`
  - Provides UI-facing gesture handling integrated with Framer Motion
  - Dispatches events to gesture reducer: `dispatchGestureEvent(event)`
  - Manages side effects: animation controls, completion callbacks, error handling
  - Integrates with existing `onSwipeComplete` callback and zen lock

### Event-driven pattern
Components dispatch **events** (declarative intent) rather than mutating local state:
```javascript
// On pointer down:
dispatchGestureEvent({ type: GestureEventType.DRAG_STARTED })

// On successful drag completion:
dispatchGestureEvent({ type: GestureEventType.DRAG_FINISHED })

// On drag failure:
dispatchGestureEvent({
  type: GestureEventType.DRAG_FAILED,
  errorMessage: 'Failed to remove article'
})
```

### Design rationale

**Why a reducer for Domain D?**
- Explicit transition modeling for drag lifecycle prevents impossible states
- Error state management benefits from centralized logic
- Integration with existing interaction patterns (drag thresholds, animation timing)
- Maintains consistency with other domain reducers (A, B)

**Why keep scope local to swipe behavior?**
- Select-mode already managed globally in `interactionReducer`
- Gesture drag state is component-local concern
- Avoids cross-domain orchestration overhead
- Maintains separation of concerns

### Storage integration
Gesture state is **ephemeral** (not persisted):
- Component-local state reset on unmount
- No Supabase sync required
- Error state shown temporarily then cleared

---

## Selectable Pattern (Updated)

Components that support selection behavior are wrapped in `Selectable`. This is a composition wrapper that encapsulates:
- Long press gesture detection (`useLongPress`)
- Dispatching selection events to the interaction reducer (`useInteraction`)
- Rendering a checkmark overlay for selected items

Important behavioral rule:
- Long press toggles selection in any mode.
- Short press behavior is owned by the interactive child:
  - Items: handled by `ArticleCard` (calls `itemShortPress`)
  - Containers: handled by `FoldableContainer` (calls `containerShortPress`)

### Usage (container):

```jsx
// ... existing code ...
<Selectable id={componentId} descendantIds={descendantIds}>
  <FoldableContainer id={componentId} /* ... existing props ... */>
    {/* ... existing content ... */}
  </FoldableContainer>
</Selectable>
// ... existing code ...
```

### Usage (item):

```jsx
// ... existing code ...
<Selectable id={articleId} disabled={isRemoved}>
  <ArticleCard /* ... existing props ... */ />
</Selectable>
// ... existing code ...
```

### ID formats (selection + containers):

| Component     | ID Pattern                             | Example                                  |
|---------------|----------------------------------------|------------------------------------------|
| CalendarDay   | `calendar-{date}`                      | `calendar-2026-01-28`                   |
| NewsletterDay | `newsletter-{date}-{source_id}`        | `newsletter-2026-01-28-tldr_tech`       |
| Section       | `section-{date}-{source_id}-{sectionKey}` | `section-2026-01-28-tldr_tech-AI`     |
| ArticleCard   | `article-{url}`                        | `article-https://example.com/article`   |

---

## Call Graph

> Focus: Component dependency and execution hierarchy.

```
main()
├── App (Root)
│   ├── useEffect (Initial Load)
│   │   ├── sessionStorage cache check (10min TTL)
│   │   └── loadFeed() [if cache miss/stale]
│   │       ├── getDailyPayloadsRange() → setResults (immediate render)
│   │       │   └── fetch('/api/storage/daily-range')
│   │       └── scrapeNewsletters() → mergeIntoCache (background)
│   │           └── fetch('/api/scrape')
│   │
│   ├── Header Area
│   │   ├── SelectionCounterPill (visible iff selectedIds.size > 0)
│   │   └── ScrapeForm (Settings)
│   │       ├── useSupabaseStorage('cache:enabled')
│   │       └── validateDateRange()
│   │
│   └── Feed (Main Content)
│       └── CalendarDay (Iterated by Date)
│           ├── useSupabaseStorage(scrapes:date)  ← seeds cache, no fetch
│           └── Selectable (long press dispatch)
│               └── FoldableContainer (short press: expand/collapse via interaction layer)
│                   └── NewsletterDay (Iterated by Issue)
│                       └── Selectable
│                           └── FoldableContainer
│                               ├── Section (If newsletter has sections)
│                               │   └── Selectable
│                               │       └── FoldableContainer
│                               │           └── ArticleList
│                               │
│                               └── ArticleList (If no sections)
│                                   └── ArticleCard (Iterated by Article)
│                                       └── Selectable (long press selection)
│                                           ├── useArticleState()
│                                           ├── useSummary()
│                                           ├── useSwipeToRemove()
│                                           │   └── useAnimation(Framer Motion)
│                                           │
│                                           └── ZenModeOverlay (Conditional; short press open depends on interaction reducer)
│                                               ├── useScrollProgress()
│                                               ├── useOverscrollUp()
│                                               └── usePullToClose()
```

---

## Sequence Diagram

> Focus: The "Reading Flow"—from clicking a card to marking it as removed.

```
TIME   ACTOR              ACTION                                TARGET
│
├───►  User               Clicks Article Card               ──► ArticleCard
│
├───►  ArticleCard        Delegates click decision          ──► itemShortPress(articleId)
│                         (Normal: open / Select: toggle)
│
├───►  ArticleCard        Checks TLDR availability          ──► useSummary
│      │
│      ├── (If missing)   Request TLDR Generation           ──► API (/summarize-url)
│      │   API            Returns Markdown/HTML             ──► useSummary
│      │
│      └── (If ready)     Expands Overlay                   ──► ZenModeOverlay
│
├───►  User               Reads Content (Scrolls)           ──► ZenModeOverlay
│      ZenModeOverlay     Updates Progress Bar              ──► UI (Visual)
│
├───►  User               Overscrolls Up (Pull to finish)   ──► useOverscrollUp
│
├───►  useOverscrollUp    Triggers "Complete"               ──► ArticleCard
│
├───►  ArticleCard        1. Collapses Overlay              ──► UI
│                         2. Marks as Read & Removed        ──► useArticleState
│                         3. Animates Card Exit             ──► Framer Motion
│
├───►  useArticleState    Dispatches lifecycle event        ──► articleLifecycleReducer
│                         (MARK_REMOVED)                        (Domain A)
│
└───►  useArticleState    Persists State Change             ──► API (/storage)
```

## Data Flow Diagram

> Focus: Transformation of data from Raw API Payload to Persisted User State.

```
[ PHASE 1: CACHE ]      [ CACHE SEED ]         [ PRESENTATION ]       [ PERSISTENCE ]
(/api/storage/           (No extra fetch)       (UI Rendering)         (Syncing)
 daily-range)

┌──────────────┐     ┌──────────────────┐   ┌────────────────┐     ┌──────────────┐
│ Cached       │────►│ CalendarDay      │──►│ Feed Grouping  │────►│ DOM Output   │
│ Payloads     │     │ seeds readCache  │   │ (Date/Issue)   │     │ (HTML)       │
└──────────────┘     └──────────────────┘   └────────────────┘     └──────────────┘

[ PHASE 2: SCRAPE ]
(/api/scrape,
 background)

┌──────────────┐     ┌──────────────────┐   ┌────────────────┐
│ Fresh        │────►│ mergeIntoCache() │──►│ emitChange()   │──► All subscribers re-render
│ Payloads     │     │ overlay local    │   │ notifies subs  │    (new articles appear)
└──────────────┘     │ user state       │   └────────────────┘
                     └──────────────────┘

[ USER ACTIONS ]

                     ┌──────────────────┐   ┌────────────────┐
                     │ setValueAsync()  │──►│ emitChange()   │
                     │ updates cache    │   │ notifies subs  │
                     └────────┬─────────┘   └───────┬────────┘
                              │                     │
                              ▼                     ▼
                     ┌────────────────┐     ┌────────────────┐
                     │ API /storage   │     │ All components │
                     │ (persist)      │     │ re-render      │
                     └────────────────┘     └────────────────┘
```

## Two-Phase Loading (Background Rescrape)

On mount, `App.jsx` loads the feed in two phases so that cached articles display immediately while a background rescrape runs for stale dates (today).

### Phase 1 — Cache read (~100ms)
`getDailyPayloadsRange(startDate, endDate)` fetches cached payloads from Supabase. If data exists, `setResults` renders the feed immediately. CalendarDay components mount and seed `readCache` with these payloads.

### Phase 2 — Background scrape (seconds)
`scrapeNewsletters(startDate, endDate)` fires concurrently with phase 1. When it resolves:
- For dates already rendered: `mergeIntoCache(key, mergeFn)` writes the merged payload into `readCache` and calls `emitChange`. All `useSupabaseStorage` subscribers for that key re-render — new articles appear in place.
- For new dates not in the cache: appended to `results.payloads` so Feed renders additional CalendarDay components.

### Merge strategy (`mergePreservingLocalState`)
The merge overlays local user state (`tldr`, `read`, `removed`) on top of the server's fresh payload. This prevents the background scrape from reverting optimistic changes the user made during the scrape window.

### `mergeIntoCache` (useSupabaseStorage.js)
Module-level export that writes directly to `readCache` and calls `emitChange`, bypassing the "seed only if empty" guard that CalendarDay uses. This is the mechanism for pushing data into already-mounted components from outside the hook.

### Logging
Feed-level transitions are logged via `logTransition('feed', range, from, to, extra)` and appear in the quake console:
- `idle → ready` (sessionStorage hit)
- `idle → fetching` (cache miss, requests fired)
- `fetching → cached` (phase 1 rendered)
- `cached → merged` (phase 2 complete, with new article/day counts)
- `fetching → ready` (no cache existed, direct render from scrape)
