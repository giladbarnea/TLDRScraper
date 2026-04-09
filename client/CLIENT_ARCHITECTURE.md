---
name: client architecture
description: Client-side architecture for the Newsletter Aggregator
last_updated: 2026-04-09 09:14, 81662be
scope: exhaustively-wide, equally high level view of the entire client architecture.
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
  - Persists `expandedContainerIds` to `localStorage` (`expandedContainers:v1` key). `selectedIds` is ephemeral (resets on page reload).
  - `itemShortPress(itemId)` uses a `dispatchWithDecision` pattern: runs the reducer synchronously to read `decision.shouldOpenItem`, then dispatches the resulting state via an internal `REPLACE_STATE` event. This lets `ArticleCard` act on the decision without waiting for a re-render.
- `reducers/interactionReducer.js`
  - The single source of truth for transitions.
  - Suppression latch is time-windowed (800ms): set after every long press, consumed (cleared) on the next short press for the same target within the window.
- `hooks/useLongPress.js`
  - Pointer-event long press detection for mobile and desktop.

### Component responsibilities
- **Selectable**
  - Detects long press and dispatches LONG_PRESS events to the interaction layer.
  - `isParent = descendantIds.length > 0`. Only leaf items (`isParent = false`) render the checkmark ring overlay. Containers dispatch `CONTAINER_LONG_PRESS` to toggle all descendant articles but display no selected state themselves.
  - `onPointerDown` calls `e.stopPropagation()` before forwarding to `useLongPress`. This prevents nested Selectables from double-firing (e.g., an ArticleCard long press does not also trigger its enclosing CalendarDay Selectable).
- **ArticleCard**
  - On click, calls `itemShortPress(articleId)`:
    - In Normal mode: returns "should open" → opens TLDR/Zen overlay.
    - In Select mode: toggles selection (no open).
  - Calls `registerDisabled(articleId, isRemoved)` in a `useEffect`. This links article lifecycle (Domain A) to the interaction layer: when an article is removed, the reducer removes it from `selectedIds` and blocks future selection.
  - Derives `swipeEnabled = canDrag && !isSelectMode` — disables Framer Motion drag when in select mode.
- **FoldableContainer**
  - On click, calls `containerShortPress(containerId)` to expand/collapse, regardless of selection mode.
  - On mount (when `defaultFolded` is true), calls `setExpanded(id, false)` to push initial collapsed state into the shared `expandedContainerIds` set.

---

See [ALL_STATES.md](ALL_STATES.md#3-interaction) for the Interaction state machine specification (states, events, transitions, suppress latch behavior).

---

## Article Lifecycle (Domain A)

Article lifecycle (`unread` → `read` → `removed`) is managed via a closed reducer pattern. Components dispatch events declaratively; the reducer returns a storage patch applied via `useSupabaseStorage`. See [ALL_STATES.md](ALL_STATES.md#1-article-lifecycle) for states, events, and transitions.

**Key modules:** `reducers/articleLifecycleReducer.js`, `hooks/useArticleState.js`

---

## Summary (Domain B + View State)

Summary management separates **data state** (reducer: `unknown → loading → available/error`) from **view state** (simple `useState` for expanded/collapsed). The `useSummary` hook orchestrates both. See [ALL_STATES.md](ALL_STATES.md#2-summary-data) for the data state machine.

**Key modules:** `reducers/summaryDataReducer.js`, `hooks/useSummary.js`, `lib/markdownUtils.js` (markdown→HTML conversion with KaTeX support), `lib/zenLock.js` (mutual-exclusion lock), `lib/requestUtils.js` (request tokens)

---

## Gesture / Swipe-to-Remove (Domain D)

Swipe-to-remove gesture state (`idle` → `dragging` → `error`) is managed via a per-article reducer. See [ALL_STATES.md](ALL_STATES.md#4-gesture-swipe-to-remove) for the state machine specification.

**Key modules:** `reducers/gestureReducer.js`, `hooks/useSwipeToRemove.js`

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
│   ├── useFeedLoader (Feed Loading Hook)
│   │   └── loadFeed() → session cache → phase 1 (cached) → phase 2 (scrape + merge)
│   │
│   ├── useEffect (Initial Load)
│   │   └── loadFeed({ startDate, endDate, useSessionCache: true })
│   │
│   ├── Header Area
│   │   ├── SelectionCounterPill (visible iff selectedIds.size > 0)
│   │   └── ScrapeForm (Settings)
│   │       ├── useFeedLoader.getDefaultFeedDateRange()
│   │       └── loadFeed({ startDate, endDate })
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
│                                               └── BaseOverlay
│                                                   ├── useScrollProgress()
│                                                   ├── useOverscrollUp()
│                                                   └── usePullToClose()
```

**Note:** `BaseOverlay` is the shared foundation for both `ZenModeOverlay` and `DigestOverlay`. It handles body scroll lock, escape key, scroll progress, pull-to-close, and overscroll-up gestures. The overlay wrappers provide only header content and prose-styled children.

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
                     (lib/feedMerge.js)

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

### Unified Feed Loading

Both entry points flow through `useFeedLoader.loadFeed()`:

```
App.jsx mount
    │
    └── loadFeed({ useSessionCache: true })
              │
ScrapeForm.jsx submit
    │
    └── loadFeed({ useSessionCache: false })
              │
              ▼
        useFeedLoader
              │
              ├─► Session cache check (10min TTL)
              ├─► Phase 1: getDailyPayloadsRange() → cached render
              └─► Phase 2: scrapeNewsletters() + mergePreservingLocalState()
```

## Two-Phase Loading (Background Rescrape)

On mount, `App.jsx` delegates to `useFeedLoader` which loads the feed in two phases so that cached articles display immediately while a background rescrape runs for stale dates (today).

### Phase 1 — Cache read (~100ms)
`getDailyPayloadsRange(startDate, endDate)` fetches cached payloads from Supabase. If data exists, `setResults` renders the feed immediately. CalendarDay components mount and seed `readCache` with these payloads.

### Phase 2 — Background scrape (seconds)
`scrapeNewsletters(startDate, endDate)` is awaited sequentially *after* phase 1 resolves to prevent heavy background tasks from choking network bandwidth during the initial render. When it resolves:
- For dates already rendered: `mergeIntoCache(key, mergeFn)` writes the merged payload into `readCache` and calls `emitChange`. All `useSupabaseStorage` subscribers for that key re-render — new articles appear in place.
- For new dates not in the cache: appended to `results.payloads` so Feed renders additional CalendarDay components.

### Unified Entry Point
Both `App.jsx` (on mount) and `ScrapeForm.jsx` (on submit) call `useFeedLoader.loadFeed()`. This ensures consistent cache-first + merge behavior regardless of entry point. The hook encapsulates session cache (10min TTL), two-phase loading, and merge logic.

### Merge strategy (`mergePreservingLocalState`)
The merge spreads the cached article and overlays only server-origin fields (`SERVER_ORIGIN_FIELDS`: url, title, category, etc.) from the fresh payload. Any client-state field (`summary`, `read`, `removed`, and future additions) is preserved automatically. This prevents the background scrape from reverting optimistic changes the user made during the scrape window.

**Module:** `lib/feedMerge.js` — contains `mergePreservingLocalState()` and `SERVER_ORIGIN_FIELDS` constant.

**`issueDate` authority:** `issueDate` is forced to `freshPayload.date` during merge (not carried from server article data), and CalendarDay stamps `issueDate: date` on every article at render time. CalendarDay owns the storage key, so it is the authoritative source for `issueDate`. This prevents silent click failures when adapters return a `date` that differs from the payload's day. See `GOTCHAS.md` 2026-02-15.

### `mergeIntoCache` (useSupabaseStorage.js)
Module-level export that writes directly to `readCache` and calls `emitChange`, bypassing the "seed only if empty" guard that CalendarDay uses. This is the mechanism for pushing data into already-mounted components from outside the hook.

### Logging
Feed-level transitions are logged via `logTransition('feed', range, from, to, extra)` and appear in the quake console:
- `idle → ready` (sessionStorage hit)
- `idle → fetching` (cache miss, requests fired)
- `fetching → cached` (phase 1 rendered)
- `cached → merged` (phase 2 complete, with new article/day counts)
- `fetching → ready` (no cache existed, direct render from scrape)

**Module:** `hooks/useFeedLoader.js` — owns the logging for feed loading transitions.
