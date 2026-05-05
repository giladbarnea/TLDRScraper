---
name: client/feed-loading
description: Client-side two-phase feed loading and merge algorithm.
last_updated: 2026-05-05 06:38, 36614cc
---
# Client: Feed Loading

[→ Server: Scraping Pipeline](../server/scraping-pipeline.md) | [→ State Machines: Feed & Storage](../state-machines/feed-and-storage.md)

## Data Flow Diagram

> Focus: Transformation of API payloads into rendered structure plus live article state.

```
[ PHASE 1: CACHE ]      [ STORE HYDRATION ]    [ PRESENTATION ]       [ PERSISTENCE ]
(/api/storage/           (No extra fetch)       (UI Rendering)         (Syncing)
 daily-range)

┌──────────────┐     ┌──────────────────┐   ┌────────────────┐     ┌──────────────┐
│ Cached       │────►│ CalendarDay      │──►│ Feed Grouping  │────►│ DOM Output   │
│ Payloads     │     │ hydrateDay()     │   │ (Date/Issue)   │     │ (HTML)       │
└──────────────┘     └──────────────────┘   └────────────────┘     └──────────────┘

[ PHASE 2: SCRAPE ]
(/api/scrape,
 background)

┌──────────────┐     ┌──────────────────┐   ┌────────────────┐
│ Fresh        │────►│ mergeDayFrom     │──►│ articleStore   │──► Slice subscribers update
│ Payloads     │     │ Server()         │   │ notifies subs  │    (new articles appear)
└──────────────┘     │ user state       │   └────────────────┘
                     └──────────────────┘
                     (store/articleStore.js)

[ USER ACTIONS ]

                     ┌──────────────────┐   ┌────────────────┐
                     │ queueDaily...    │──►│ articleStore   │
                     │ optimistic patch │   │ notifies slice │
                     └────────┬─────────┘   └───────┬────────┘
                              │                     │
                              ▼                     ▼
                     ┌────────────────┐     ┌────────────────┐
                     │ API /storage   │     │ Affected       │
                     │ daily payload  │     │ components     │
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
              ├─► Request token ownership
              ├─► Session cache check (30min TTL) → hydrate payloads → setResults()
              ├─► Phase 1: getDailyPayloadsRange() → hydrate payloads → cached render
              └─► Phase 2: scrapeNewsletters() → merge fresh payloads into articleStore
```

`useFeedLoader` owns the app-level result shape and request cancellation. Before any cached, session, or fresh payload reaches `setResults()`, the payload is ingested by `store/articleStore.js`.

Existing rendered dates are merged with `mergeDayFromServer(date, payload)`, which keeps local lifecycle, summary, digest, selection, and expansion state while accepting server-origin scrape fields. Newly rendered dates are initialized with `hydrateDay(date, payload)`. The rendered tree still receives structural props, but live article/day state is read from `articleStore` subscriptions.
