---
name: state-machines/interaction-and-gestures
description: State machines for selection interaction, container expansion, and swipe gestures.
last_updated: 2026-05-05 20:55
---
# State Machines: Interaction and Gestures

[→ Client: Interaction & Selection](../client/interaction-and-selection.md) | [→ Client: Gestures](../client/gestures.md)

### 3. Interaction

| | |
|---|---|
| **Pattern** | Pure reducer driven by `articleStore` external-store actions |
| **File** | `reducers/interactionReducer.js`, `store/articleStore.js` |
| **Scope** | Global module-level store |

#### State Shape

```js
{
  selected:               boolean,       // stored on article slices only
  selectedCount:          number,        // derived select-mode count
  selectedDescriptors:    Array<object>, // derived selected article metadata
  expandedContainerIds:   Set<string>,   // "calendar-{date}", "newsletter-…", "section-…"
  suppressNextShortPress: { id, untilMs } // anti-double-fire latch
}
```

Derived: `isSelectMode = selectedCount > 0`.

#### Events

| Event | Effect | Dispatched from |
|---|---|---|
| `ITEM_LONG_PRESS` | Toggle the item article slice + set suppress latch | `Selectable` (article long-press) |
| `CONTAINER_LONG_PRESS` | Toggle all descendant article slices + set suppress latch | `Selectable` (container long-press) |
| `ITEM_SHORT_PRESS` | If suppressed → consume latch. If select mode → toggle selection. Else → return `{ shouldOpenItem: true }` | `Selectable` → `ArticleCard` click handler |
| `CONTAINER_SHORT_PRESS` | If suppressed → consume latch. Else → toggle expand | `FoldableContainer` click |
| `CLEAR_SELECTION` | Clear selected article slices | Selection pill, `App.jsx` after batch ops, `useDigest` after trigger |
| `SET_EXPANDED` | Explicitly set expand state for a container | `FoldableContainer` `defaultFolded` effect |

#### The Suppress Latch

After a long-press, an 800ms window prevents the subsequent touchend's short-press from accidentally toggling expand or opening a summary. Targeted: only suppresses the same ID that was long-pressed.

#### Persistence

`expandedContainerIds` is persisted to `localStorage` under key `expandedContainers:v1` (JSON array). Hydrated on init. Selection is ephemeral.

Removed articles are blocked through an `isDisabled(id)` predicate passed to the reducer. The predicate resolves the article slice and returns true for removed articles, so disabled state is not duplicated.

---

### 9. Container Expansion (localStorage)

| | |
|---|---|
| **Pattern** | Part of `articleStore` state, persisted to `localStorage` |
| **File** | `store/articleStore.js` |
| **Scope** | Global |

**Note:** `hooks/useLocalStorage.js` exists but is **unused**. Container persistence is handled inside `articleStore`.

#### Storage

Single key: `expandedContainers:v1` → JSON array of container IDs.

#### Container ID Patterns

| Pattern | Source | Example |
|---|---|---|
| `calendar-{date}` | `CalendarDay` | `calendar-2024-01-15` |
| `newsletter-{date}-{sourceId}` | `NewsletterDay` | `newsletter-2024-01-15-tldr_tech` |
| `section-{date}-{sourceId}-{sectionKey}` | `NewsletterDay/Section` | `section-2024-01-15-tldr_tech-Web Dev` |

#### Auto-Collapse And Removed Ordering

`FoldableContainer` accepts `defaultFolded`. `CalendarDay` uses `useDayArticlesSummary(date)` for day-level all-removed state. Newsletter and section containers receive grouped lifecycle state from `RemovedOrderSlot`, which subscribes through `useAllArticlesRemoved(date, urls)` for their specific article URL sets. Passing `defaultFolded={true}` triggers `interactionActions.setExpanded(id, false)` — removing the ID from `expandedContainerIds` and persisting.

`RemovedOrderSlot` also gives all-removed groups a high flex order, so fully removed sections sink within a newsletter and fully removed newsletters sink within their calendar day using the same live grouped read model that drives dimming and auto-collapse.

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
