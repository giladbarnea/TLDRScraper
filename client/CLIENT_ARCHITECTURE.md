---
name: client architecture
description: Client-side architecture for the Newsletter Aggregator
last_updated: 2026-01-28 19:44
---
# Client Architecture

## Overview
This document maps the frontend architecture of the Newsletter Aggregator. It details:
 * System Boundaries: How the React client interacts with the backend API.
 * Rendering Hierarchy: The component tree structure and dependencies.
 * Interaction Flow: The chronological steps of user actions (Scraping, Reading, Archiving).
 * Data Transformation: How raw API payloads are enriched with user state and persisted.

---

The client is built as a Single Page Application (SPA) using React and Vite. It relies heavily on an Optimistic UI pattern where local state updates immediately for the user while syncing asynchronously to the backend via useSupabaseStorage. The architecture uses **scrape-first hydration**: `/api/scrape` is the authoritative data source, and CalendarDay seeds the storage cache with this payload on mount—eliminating redundant per-day storage fetches while preserving pub/sub reactivity for state changes. The architecture emphasizes "Zen Mode" reading, dividing the view into a Feed (browsing) and an Overlay (reading).

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
│         │ /scrape  │          │ /storage │        │ /tldr-url │         │
│         └──────────┘          └──────────┘        └───────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Selectable Pattern

Components that need podcast source selection capability use the `Selectable` wrapper. This is a render-props composition pattern that encapsulates:
- Menu open/close state
- Three-dot menu button
- Bottom sheet with "Select" action
- localStorage persistence for podcast source tracking

**Usage:**
```jsx
<Selectable id={componentId} title={displayTitle}>
  {({ menuButton, openMenu }) => (
    <FoldableContainer rightContent={menuButton}>
      {/* component content */}
    </FoldableContainer>
  )}
</Selectable>
```

**Render props provided:**
- `menuButton` - Pre-configured ThreeDotMenuButton, place in layout
- `openMenu` - Function to programmatically open the menu (e.g., from ZenModeOverlay)

**ID formats for podcast source selection:**
| Component | ID Pattern | Example |
|-----------|------------|---------|
| CalendarDay | `calendar-{date}` | `calendar-2026-01-28` |
| NewsletterDay | `newsletter-{date}-{source_id}` | `newsletter-2026-01-28-tldr_tech` |
| Section | `section-{date}-{source_id}-{sectionKey}` | `section-2026-01-28-tldr_tech-AI` |
| ArticleCard | `article-{url}` | `article-https://example.com/article` |

---

## Call Graph
> Focus: Component dependency and execution hierarchy.

```
main()
├── App (Root)
│   ├── useEffect (Initial Load)
│   │   ├── sessionStorage cache check (10min TTL)
│   │   └── scrapeNewsletters() [if cache miss/stale]
│   │       └── fetch('/api/scrape')
│   │
│   ├── Header Area
│   │   └── ScrapeForm (Settings)
│   │       ├── useSupabaseStorage('cache:enabled')
│   │       └── validateDateRange()
│   │
│   └── Feed (Main Content)
│       └── CalendarDay (Iterated by Date)
│           ├── useSupabaseStorage(scrapes:date)  ← seeds cache, no fetch
│           └── Selectable (render props: menuButton, openMenu)
│               └── FoldableContainer
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
│                                       └── Selectable
│                                           ├── useArticleState()
│                                           ├── useSummary()
│                                           ├── useSwipeToRemove()
│                                           │   └── useAnimation(Framer Motion)
│                                           │
│                                           └── ZenModeOverlay (Conditional)
│                                               ├── useScrollProgress()
│                                               ├── useOverscrollUp()
│                                               └── usePullToClose()
```
---

## Sequence Diagram
> Focus: The "Reading Flow"—from clicking a card to marking it as done.

```
TIME   ACTOR              ACTION                                TARGET
│
├───►  User               Clicks Article Card               ──► ArticleCard
│
├───►  ArticleCard        Checks TLDR availability          ──► useSummary
│      │
│      ├── (If missing)   Request TLDR Generation           ──► API (/tldr-url)
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
└───►  useArticleState    Persists State Change             ──► API (/storage)

Data Flow Diagram
Focus: Transformation of data from Raw API Payload to Persisted User State.
[ SOURCE ]           [ CACHE SEED ]         [ PRESENTATION ]       [ PERSISTENCE ]
(/api/scrape)        (No extra fetch)       (UI Rendering)         (Syncing)

┌──────────────┐     ┌──────────────────┐   ┌────────────────┐     ┌──────────────┐
│ API Response │────►│ CalendarDay      │──►│ Feed Grouping  │────►│ DOM Output   │
│ (Newsletters)│     │ seeds readCache  │   │ (Date/Issue)   │     │ (HTML)       │
└──────────────┘     └────────┬─────────┘   └────────────────┘     └──────────────┘
                              │
                              │ (User Action: Read/Remove)
                              │
                     ┌────────▼─────────┐   ┌────────────────┐
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
