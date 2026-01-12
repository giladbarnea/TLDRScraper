---
name: client architecture
description: Client-side architecture for the Newsletter Aggregator
last_updated: 2026-01-12 20:07, 9c32495
---
# Client Architecture

## Overview
This document maps the frontend architecture of the Newsletter Aggregator. It details:
 * System Boundaries: How the React client interacts with the backend API.
 * Rendering Hierarchy: The component tree structure and dependencies.
 * Interaction Flow: The chronological steps of user actions (Scraping, Reading, Archiving).
 * Data Transformation: How raw API payloads are enriched with user state and persisted.

---

The client is built as a Single Page Application (SPA) using React and Vite. It relies heavily on an Optimistic UI pattern where local state updates immediately for the user while syncing asynchronously to the backend via useSupabaseStorage. The architecture emphasizes "Zen Mode" reading, dividing the view into a Feed (browsing) and an Overlay (reading).

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

## Call Graph
> Focus: Component dependency and execution hierarchy.

```
main()
├── App (Root)
│   ├── useEffect (Initial Load)
│   │   └── scrapeNewsletters()
│   │       └── fetch('/api/scrape')
│   │
│   ├── Header Area
│   │   └── ScrapeForm (Settings)
│   │       ├── useSupabaseStorage('cache:enabled')
│   │       └── validateDateRange()
│   │
│   └── Feed (Main Content)
│       └── CalendarDay (Iterated by Date)
│           ├── useSupabaseStorage(scrapes:date)
│           └── FoldableContainer
│               └── NewsletterDay (Iterated by Issue)
│                   ├── FoldableContainer
│                   └── ArticleList
│                       └── ArticleCard (Iterated by Article)
│                           ├── useArticleState()
│                           ├── useSummary()
│                           ├── useSwipeToRemove()
│                           │   └── useAnimation(Framer Motion)
│                           │
│                           └── ZenModeOverlay (Conditional Render)
│                               ├── useScrollProgress()
│                               ├── useOverscrollUp()
│                               └── usePullToClose()
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
[ SOURCE ]           [ ENRICHMENT ]         [ PRESENTATION ]       [ PERSISTENCE ]
(Raw JSON)           (Merging State)        (UI Rendering)         (Syncing)

                     ┌──────────────────┐
                     │ useSupabaseStore │
                     │ (Fetch/Cache)    │
                     └────────┬─────────┘
                              │
┌──────────────┐     ┌────────▼─────────┐   ┌────────────────┐     ┌──────────────┐
│ API Response │────►│ Live Payload     │──►│ Feed Grouping  │────►│ DOM Output   │
│ (Newsletters)│     │ (Merged Data)    │   │ (Date/Issue)   │     │ (HTML)       │
└──────────────┘     └────────┬─────────┘   └────────────────┘     └──────────────┘
                              │
                              │ (User Action: Read/Remove)
                              │
                     ┌────────▼─────────┐   ┌────────────────┐
                     │ Optimistic Upd.  │──►│ Write Queue    │
                     │ (Local React)    │   │ (Debounced)    │
                     └──────────────────┘   └───────┬────────┘
                                                    │
                                                    ▼
                                            ┌────────────────┐
                                            │ API /storage   │
                                            └────────────────┘
```
