---
name: state-machines/architecture-and-flows
description: Cross-cutting topology, coupling matrices, and cross-machine user flows.
last_updated: 2026-05-05 12:01
---
# State Machines: Architecture and Flows

### Topology: How They're Wired

The client machines form a layered architecture. Pure reducers define transitions; `articleStore` owns live client state; mutation queues persist changes back to Supabase daily payloads.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: OVERLAYS (ephemeral portals)                                      │
│                                                                             │
│  ZenModeOverlay       DigestOverlay       ToastContainer                    │
│       │                    │                   │                            │
│       └─────────┬──────────┘                   │                            │
│                 ▼                              ▼                            │
│            BaseOverlay                      toastBus                        │
│      scroll lock, Escape, reader layers                                      │
│                 ▲                                                           │
│                 │ zen lock                                                   │
├─────────────────┼───────────────────────────────────────────────────────────┤
│  LAYER 3: DOMAIN HOOKS                                                       │
│                                                                             │
│  useSummary        useDigest        useArticleState        useSwipeToRemove │
│       │                │                  │                       │          │
│       └────────┬───────┴──────────┬───────┘                       │          │
│                ▼                  ▼                               ▼          │
│        dailyPayloadMutations   articleStore                 gestureReducer   │
├─────────────────────────────────────────────────────────────────────────────┤
│  LAYER 2: PURE REDUCERS                                                      │
│                                                                             │
│  articleLifecycleReducer   summaryDataReducer   interactionReducer          │
├─────────────────────────────────────────────────────────────────────────────┤
│  LAYER 1: CLIENT STATE + PERSISTENCE                                         │
│                                                                             │
│  articleStore: article/day/container/selection subscriptions                 │
│  dailyPayloadMutations: optimistic queue + conflict refresh + rollback       │
│  storageApi: daily payload HTTP boundary                                     │
│  localStorage: expanded container IDs                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  LAYER 0: DATA LOADING                                                       │
│                                                                             │
│  useFeedLoader: session cache, daily-range cache, scrape, store hydration    │
│  ScrapeForm: date validation and React 19 action-state submit flow           │
└─────────────────────────────────────────────────────────────────────────────┘
```

Scrape Form calls `useFeedLoader.loadFeed()` directly, so app mount and explicit user scrapes share the same cache-first, hydrate, and merge flow.

---

### Coupling Matrix

Each cell shows the direction of the relationship. Read as "row affects/uses column".

| | Article Lifecycle | Summary Data | Interaction | Gesture | Feed Loading | Digest | Summary View | Article Store / Mutations | BaseOverlay | Toast |
|---|---|---|---|---|---|---|---|---|---|---|
| **Article Lifecycle** | — | — | Disables selection through `isDisabled` | — | — | Marks consumed | Marks read on close | Optimistic patch + persist | — | — |
| **Summary Data** | — | — | — | — | — | Shared reducer | Drives overlay content | Optimistic patch + persist | — | Emits toast |
| **Interaction** | Guards selection | Filters actionable | — | Blocks swipe in select mode | — | Clears after trigger | — | Stores selection/expansion | — | — |
| **Gesture** | Calls toggle remove | — | Blocked by select mode | — | — | — | — | Persists lifecycle patch | — | — |
| **Feed Loading** | Hydrates fields | Hydrates fields | Preserves selection | — | — | Hydrates digest | — | Hydrates/merges days | — | — |
| **Digest** | Marks articles read/removed | Marks loading, restores | Clears selection | — | Reads selected descriptors | — | Shares zen lock | Writes article + day patches | Composes | — |
| **Summary View** | Marks read via `ArticleCard` | Dispatches summary events | — | — | — | Shares zen lock | — | Writes article summary/view state | Composes | Emits toast |
| **Article Store / Mutations** | Stores slice | Stores slice | Stores selection/expansion | — | Ingests payloads | Stores digest | Stores `expandedView` | — | — | — |
| **BaseOverlay** | `onMarkRemoved` | — | — | — | — | Composed by Digest | Composed by Zen | — | — | — |
| **Toast** | — | — | — | — | — | — | Click → `expand()` | — | — | — |

The overlay context menu sits outside the data matrix because its coupling is DOM and layer based: overlay wrappers instantiate the menu/elaboration hooks, `BaseOverlay` owns the reader `FloatingNode`, and `ElaborationPreview` renders in the overlay layer slot.

---

### Key Cross-Machine Flows

#### Flow 1: User taps an article

```
ArticleCard click
      │
interactionActions.itemShortPress(articleId)
      │
      ├─ suppressed → consume latch, no-op
      ├─ select mode → toggle selected article slice
      └─ normal mode → summary.toggle(effort)
                         │
                         ├─ unavailable → fetchSummary()
                         │                  │
                         │                  ├─ summaryActions.request()
                         │                  ├─ POST /api/summarize-url
                         │                  ├─ summaryActions.succeed/fail()
                         │                  └─ queueDailyArticlePatch()
                         │
                         └─ available → acquireZenLock(url)
                                        summaryActions.expand(articleKey)
                                        ZenModeOverlay renders
```

#### Flow 2: User swipes an article left

```
touch start on card
      │
canDrag = !isRemoved && !stateLoading && !isSelectMode
      │
      ├─ disabled → no-op
      └─ enabled → Gesture: DRAG_STARTED
                    Framer Motion drag active
                         │
                         ├─ release before threshold → DRAG_FINISHED, snap back
                         └─ release past threshold → animate off-screen
                                                   toggleRemove()
                                                   articleLifecycleReducer
                                                   queueDailyArticlePatch()
                                                   articleStore notifies article/day/select listeners
                                                   all-removed summaries can auto-fold containers
```

#### Flow 3: User triggers a digest

```
Long-press to select 2+ articles
      │
articleStore selected slices + selected descriptor cache
      │
SelectionActionDock "Digest"
      │
useDigest.trigger(selectedDescriptors)
      │
      ├─ same URL-set cache hit → acquireZenLock('digest'), expand
      └─ new URL-set
            │
            ├─ queueBatchArticlePatches(summary → LOADING)
            ├─ POST /api/digest
            ├─ success: restore article summaries
            ├─ success: queueDailyPayloadPatch(digest AVAILABLE)
            ├─ success: interactionActions.clearSelection()
            └─ success: acquireZenLock('digest'), expand
```

On error or abort, `useDigest` restores each affected article summary from the pre-request snapshot and writes digest error state to the target day slice.

#### Flow 4: Persistence round trip

```
User/domain action
      │
Build article or day patch
      │
Apply optimistic patch to articleStore
      │
Notify affected slice listeners
      │
PATCH /api/storage/daily/{date}/article
or PATCH /api/storage/daily/{date}
      │
      ├─ success → replaceDayFromServer(server payload)
      ├─ conflict → fetch server payload + retry once
      └─ failure → restorePayloadFromServer(date)
```

This keeps the UI fast while making the server-confirmed daily payload the durable boundary.

#### Flow 5: Feed loading → component tree hydration

```
App mount OR ScrapeForm submit
      │
useFeedLoader.loadFeed()
      │
      ├─ sessionStorage hit
      │     └─ hydrateResultPayloads() → setResults(cached)
      │
      ├─ Phase 1 daily-range cache
      │     └─ hydrateResultPayloads() → setResults(cached)
      │
      └─ Phase 2 scrape
            ├─ existing rendered date → mergeDayFromServer()
            ├─ new rendered date → hydrateDay()
            └─ setResults(fresh structural payloads)
```

After hydration, the component tree receives structural grouping props from `results`, while article cards, read/remove counters, day summaries, selection state, and overlays subscribe directly to `articleStore`.

