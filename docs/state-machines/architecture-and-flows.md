---
last_updated: 2026-05-02 10:48
---

# State Machines: Architecture and Flows

### Topology: How They're Wired

The 16 machines form a layered architecture. Understanding the layers explains why certain machines know about each other and others don't.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: OVERLAYS (ephemeral view state — portals)                        │
│                                                                             │
│  ┌──────────────────┐   ┌──────────────────┐   ┌────────────────────────┐  │
│  │ Zen Mode Overlay │   │ Digest Overlay   │   │ Toast                  │  │
│  │   + useOverlay   │   │   + useOverlay   │   └────────────────────────┘  │
│  │   ContextMenu    │   │   ContextMenu    │                              │
│  │   + useElabor.   │   │   + useElabor.   │                              │
│  └────────┬─────────┘   └────────┬─────────┘                              │
│           │                      │                                        │
│           └──────────┬───────────┘                                        │
│                      ▼                                                    │
│           ┌──────────────────────────────────────┐                        │
│           │ BaseOverlay                          │                        │
│           │  ├ ScrollProgress                   │                        │
│           │  ├ PullToClose (disabled for select)│                        │
│           │  ├ OverscrollUp                     │                        │
│           │  ├ body scroll lock                 │                        │
│           │  ├ reader FloatingNode             │                        │
│           │  ├ useDismiss (Escape only)        │                        │
│           │  └ [data-overlay-content] marker   │                        │
│           └──────────────────────────────────────┘                        │
│                      ▲                                                    │
│                      │ zen lock (mutual exclusion)                        │
├──────────────────────┼────────────────────────────────────────────────────┤
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
│  │ (useFeedLoader hook)         │──▶│ (useActionState)                  │  │
│  └──────────────────────────────┘   └───────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Note:** Scrape Form calls `useFeedLoader.loadFeed()` directly, flowing through the same cache-first + merge logic as app mount.

---

### Coupling Matrix

Each cell shows the **direction** of the relationship. Read as "row affects/uses column".

| | Art. Lifecycle | Summary Data | Interaction | Gesture | Feed Loading | Digest | Summary View | Supabase Storage | BaseOverlay | Tracked State | Toast |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Art. Lifecycle** | — | — | Disables selection | — | — | Marks consumed | Marks read on close | Persists via | — | — | — |
| **Summary Data** | — | — | — | — | — | Shared reducer | Drives overlay content | Persists via | — | — | Emits toast |
| **Interaction** | Guards selection | Filters actionable | — | Blocks swipe in select mode | — | Clears after trigger | — | — | — | — | — |
| **Gesture** | Calls toggleRemove | — | Blocked by select mode | — | — | — | — | — | — | — | — |
| **Feed Loading** | — | — | — | — | — | Provides `results` | — | Reads + merges cache | — | — | — |
| **Digest** | Marks articles read/removed | Marks articles loading, restores | Clears selection | — | Reads `results.payloads` | — | Shares zen lock | Reads + writes payload | Composes | — | — |
| **Summary View** | Marks read on close | Dispatches all events | — | — | — | Shares zen lock | — | Persists via `useArticleState` | Composes | — | Emits toast |
| **Supabase Storage** | — | — | — | — | Seeds from payloads | — | — | — | — | — | — |
| **BaseOverlay** | `onMarkRemoved` | — | — | — | — | Composed by Digest | Composed by Zen | — | Composes PullToClose, OverscrollUp, ScrollProgress | Uses via hooks | — |
| **Tracked State** | — | — | — | — | — | — | — | — | — | — | — |
| **Toast** | — | — | — | — | — | — | Click → `expand()` | — | — | — | — |

**Overlay Context Menu (§19) — coupling notes**

The context menu isn't a good fit for the matrix because its couplings are **DOM-level and event-capture-level**, not data/function level. The relationships worth remembering:

| Depends on | Direction | How |
|---|---|---|
| BaseOverlay | DOM contract | owns `[data-overlay-content]` only when `overlayMenu` is present |
| BaseOverlay | Layer contract | owns the reader `FloatingNode`, the menu render site, and the `overlayLayers` render site |
| Zen Mode Overlay | Composition | instantiates hook, passes action-bearing `overlayMenu` into BaseOverlay, and supplies `overlayLayers={<ElaborationPreview />}` |
| Digest Overlay | Composition | instantiates hook, passes action-bearing `overlayMenu` into BaseOverlay, and supplies `overlayLayers={<ElaborationPreview />}` |
| useElaboration | Indirect via action callbacks | `Elaborate` action → `runElaboration(selectedText)` (shared hook, used by both wrappers) |
| Elaboration Preview | Composition | child `FloatingNode` rendered in `overlayLayers`, above the reader and alongside the menu in the same tree |

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
   App mount OR ScrapeForm submit
       │
       └── useFeedLoader.loadFeed()
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
