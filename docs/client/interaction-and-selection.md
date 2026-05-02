---
last_updated: 2026-05-02 10:48
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

See [STATE_MACHINES.md](STATE_MACHINES.md#3-interaction) for the Interaction state machine specification (states, events, transitions, suppress latch behavior).

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
