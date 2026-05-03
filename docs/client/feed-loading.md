---
name: client/feed-loading
description: Client-side two-phase feed loading and merge algorithm.
last_updated: 2026-05-03 15:10, bb6b54a
---
# Client: Feed Loading

[→ Server: Scraping Pipeline](../server/scraping-pipeline.md) | [→ State Machines: Feed & Storage](../state-machines/feed-and-storage.md)

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
