---
name: client/reading-overlays
description: Client architecture for reading overlays including ZenMode and Digest.
last_updated: 2026-05-03 15:10, bb6b54a
---
# Client: Reading Overlays

[→ State Machines: Reading Overlays](../state-machines/reading-overlays.md)

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
│                                               ├── useOverlayContextMenu()
│                                               ├── useElaboration({ sourceMarkdown, articleUrls: [url] })
│                                               └── BaseOverlay
│                                                   ├── useScrollProgress()
│                                                   ├── useOverscrollUp()
│                                                   ├── usePullToClose() (currently enabled:false — see GOTCHAS)
│                                                   └── OverlayContextMenu (via overlayMenu contract)

App
└── DigestOverlay (Conditional; mounted while digest.expanded)
    ├── useOverlayContextMenu()
    ├── useElaboration({ sourceMarkdown: markdown, articleUrls })
    └── BaseOverlay
        └── OverlayContextMenu (via overlayMenu contract)
```

**Note:** `BaseOverlay` is the shared foundation for both `ZenModeOverlay` and `DigestOverlay`. It handles body scroll lock, reader-level Escape dismissal via Floating UI, scroll progress, pull-to-close, and overscroll-up gestures. Overlay wrappers provide header content, prose-styled children, an optional `overlayMenu` contract, and `overlayLayers` (currently `ElaborationPreview`). Both wrappers also instantiate `useElaboration`. See the "Overlay Context Menu" section above for the DOM/event and layer-stack contracts between the hook and `BaseOverlay`.

---
