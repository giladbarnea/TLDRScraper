---
name: client/interaction-and-selection
description: Client-side interaction architecture, selection modes, and foldable containers.
last_updated: 2026-05-05 20:20
---
# Client: Interaction and Selection

[→ State Machines: Interaction & Gestures](../state-machines/interaction-and-gestures.md)

## Selection and Interaction Architecture

### Goals

Selection behavior is implemented as a **declarative state machine** with a small set of events. The implementation goals are:
- Make selection mode deterministic and easy to reason about.
- Keep container expand/collapse **orthogonal** to selection.
- Ensure long-press never accidentally triggers the short-press behavior ("double fire").

### Key modules
- `store/articleStore.js`
  - Owns selected booleans on article slices, derived select mode, selected descriptor cache, expanded container IDs, and the suppress latch.
  - Exposes `interactionActions` plus small selectors: `useIsSelected(id)`, `useIsExpanded(id)`, `useIsSelectMode()`, and `useSelectedDescriptors()`.
  - Persists `expandedContainerIds` to `localStorage` (`expandedContainers:v1` key). Selection is ephemeral and resets on page reload.
- `reducers/interactionReducer.js`
  - The single source of truth for transitions.
  - Accepts an `isDisabled(id)` predicate so removed articles are blocked without maintaining a duplicated disabled-ID set.
  - Suppression latch is time-windowed (800ms): set after every long press, consumed (cleared) on the next short press for the same target within the window.
- `hooks/useLongPress.js`
  - Pointer-event long press detection for mobile and desktop.

### Component responsibilities
- **Selectable**
  - Detects long press and dispatches selection events through `interactionActions`.
  - `isParent = descendantIds.length > 0`. Only leaf items (`isParent = false`) render the checkmark ring overlay. Containers dispatch `CONTAINER_LONG_PRESS` to toggle all descendant articles but display no selected state themselves.
  - `onPointerDown` calls `e.stopPropagation()` before forwarding to `useLongPress`. This prevents nested Selectables from double-firing (e.g., an ArticleCard long press does not also trigger its enclosing CalendarDay Selectable).
- **ArticleCard**
  - On click, calls `interactionActions.itemShortPress(articleId)`:
    - In Normal mode: returns "should open" → opens TLDR/Zen overlay.
    - In Select mode: toggles selection (no open).
  - Removed articles are disabled by the reducer's `isDisabled(id)` predicate, which resolves the article slice and prevents selection.
  - Derives `swipeEnabled = canDrag && !isSelectMode` — disables Framer Motion drag when in select mode.
- **FoldableContainer**
  - On click, calls `interactionActions.containerShortPress(containerId)` to expand/collapse, regardless of selection mode.
  - On mount (when `defaultFolded` is true), calls `interactionActions.setExpanded(id, false)` to push initial collapsed state into the shared `expandedContainerIds` set.
- **RemovedOrderSlot**
  - Wraps newsletter and section containers in flex lists.
  - Subscribes to `useAllArticlesRemoved(date, urls)` once for the grouped URL set and passes the result into the rendered container.
  - Uses that same live all-removed result to sink removed groups via flex order, keeping group ordering, dimming, and auto-collapse on one store-backed read model.

---

See [State Machines: Interaction and Gestures](../state-machines/interaction-and-gestures.md#3-interaction) for the Interaction state machine specification (states, events, transitions, suppress latch behavior).

---

## Selectable Pattern (Updated)

Components that support selection behavior are wrapped in `Selectable`. This is a composition wrapper that encapsulates:
- Long press gesture detection (`useLongPress`)
- Dispatching selection events to the interaction reducer through `articleStore`
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
