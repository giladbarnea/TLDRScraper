---
last_updated: 2026-02-20 06:20
---
# Google Photos-Style Selection — Implementation Record

## Feature Summary

Long-press multi-selection across all four component levels (CalendarDay, NewsletterDay, Section, ArticleCard). Selecting a parent selects all its descendant articles. A counter pill appears in the sticky header when in select mode.

## User-Facing Behavior

1. **Long-press activation**: 500ms long-press on any card or container enters select mode and selects that target
2. **Visual indicators for selected articles**:
   - Thick grey border around the card (`ring-4 ring-slate-300`)
   - Brand-color filled checkmark in top-left corner (absolute positioned, animated)
3. **Selection counter pill**: In sticky header (right end), black pill with "✕" button + count
4. **Select mode tap behavior**:
   - Single taps on articles toggle selection (no long-press needed)
   - Deselecting the last card exits select mode
5. **Recursive selection**: Long-pressing a parent (CalendarDay/NewsletterDay/Section) selects all its descendant articles
6. **Gesture conflicts**: Swipe-to-remove disabled during select mode; long-press disabled on removed cards

## What Was NOT Built

- No localStorage sync for `selectedIds` (selection resets on page reload)
- No batch actions beyond select/deselect ("delete selected", "share selected", etc.)
- No select-all button (only recursive parent selection)
- ZenModeOverlay behavior unchanged

## Implementation

### Architecture

A single `InteractionContext` (not a separate `SelectionContext`) was introduced to manage both selection state and expand/collapse state. This unified ownership simplifies the surface area and avoids two separate providers. The context is backed by `interactionReducer.js`, a pure event-driven reducer.

`expandedContainerIds` is persisted to `localStorage` via the context (`expandedContainers:v1` key). `selectedIds` is ephemeral (resets on reload).

### Key Files

| File | Role |
|------|------|
| `contexts/InteractionContext.jsx` | Provider + `useInteraction()` hook. Exposes UI-facing functions and selectors. Persists `expandedContainerIds` to localStorage. |
| `reducers/interactionReducer.js` | Pure reducer: all state transitions. Owns suppression latch. |
| `hooks/useLongPress.js` | Pointer-event long press detection (pointer events, not touch/mouse). Cancels on move > 10px. |
| `components/Selectable.jsx` | Wrapper: attaches long-press handlers, dispatches to interaction layer, renders checkmark for leaf items. |
| `components/SelectionCounterPill.jsx` | Header pill: reads `selectedIds.size` and `clearSelection` from context. |
| `components/FoldableContainer.jsx` | Calls `containerShortPress(id)` on click; calls `setExpanded(id, false)` on mount when `defaultFolded`. |
| `lib/interactionConstants.js` | Shared constants: `LONG_PRESS_THRESHOLD_MS = 500`, `POINTER_MOVE_THRESHOLD_PX = 10`. |

### Suppression Latch

Long-press fires first; the subsequent pointer-up generates a click event that would otherwise trigger a short press. The reducer sets a time-windowed latch (800ms) on the target ID after every long press. The short press handler consumes and clears the latch, so the open/toggle action is suppressed.

### Container vs. Item Selection

`Selectable` determines its role via `isParent = descendantIds.length > 0`. Containers (parent selectables) dispatch `containerLongPress(id, descendantIds)` — which toggles all their direct article leaf descendants — and never show a checkmark overlay themselves. Only leaf articles (`isParent = false`) show the checkmark and ring.

### Wiring: Short Press Returns a Decision

`itemShortPress(itemId)` in the context uses a `dispatchWithDecision` pattern: it runs the reducer synchronously to get `decision.shouldOpenItem`, then dispatches the resulting state via `REPLACE_STATE`. This lets `ArticleCard` act on the decision immediately (e.g., open the TLDR overlay) without a re-render round-trip.

### Disabled IDs

`ArticleCard` calls `registerDisabled(componentId, isRemoved)` in a `useEffect`. The reducer removes disabled IDs from `selectedIds` if they become disabled mid-session. `Selectable` also receives `disabled={isRemoved}`, which prevents `useLongPress` from firing on removed cards.

### Swipe Conflict

`ArticleCard` sets `swipeEnabled = canDrag && !isSelectMode`. When `isSelectMode` is true, the Framer Motion `drag` prop and `dragListener` are disabled.

### ID Formats

| Component     | ID Pattern                                | Example                                    |
|---------------|-------------------------------------------|--------------------------------------------|
| CalendarDay   | `calendar-{date}`                         | `calendar-2026-01-28`                      |
| NewsletterDay | `newsletter-{date}-{source_id}`           | `newsletter-2026-01-28-tldr_tech`          |
| Section       | `section-{date}-{source_id}-{sectionKey}` | `section-2026-01-28-tldr_tech-AI`          |
| ArticleCard   | `article-{url}`                           | `article-https://example.com/article`      |
