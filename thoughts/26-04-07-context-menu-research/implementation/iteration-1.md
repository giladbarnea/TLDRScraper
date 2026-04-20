---
name: Context Menu Implementation Round 1
done: 2026-04-18, 529852a7
last_updated: 2026-04-20 13:04
---
# Context Menu Implementation Round 1

## Iteration 1 Summary

"See client files abc, checked todo items in ../xyz, and doc updates 1,2,3 in files foo bar baz"

Implements context menu triggered by mobile text selection within `ZenModeOverlay` and `DigestOverlay`. Provides quick actions ("Close reader", "Mark done") without extra UI.

## Key Changes
- **`useOverlayContextMenu.js`**: Manages state and triggers (desktop right-click, mobile text selection). Coordinates Escape key.
- **`OverlayContextMenu.jsx`**: Renders positioned portal with action buttons. Clamps to viewport. Auto-focuses first action on desktop.
- **`BaseOverlay`**: Adds `onContentContextMenu` prop. Adds `data-overlay-content` attribute to scope selection. Escape handler checks `defaultPrevented`. Disables `usePullToClose` to allow native text selection.
- **`ZenModeOverlay` & `DigestOverlay`**: Integrates hook and component with specific actions.
- **`index.css`**: Adds `overlay-menu-enter` animation.

## Implementation Details
- **Escape key coordination**: Hook intercepts Escape in capture phase via `preventDefault()` and `stopImmediatePropagation()`. Overlay's Escape handler respects `defaultPrevented`. Single Escape closes menu, not the overlay.
- **Mobile selection**: Detected via `selectionchange`, `touchstart`, and `touchend`. Validates selection anchor sits inside `[data-overlay-content]` subtree to prevent out-of-bounds triggers.

---

## Tackling the increased complexity this iteration introduced
status::pending

Coupling patterns cause this complexity. Apply these principles:

1. **Delegate to primitives.** Mobile selection, outside-click, focus, positioning, and ARIA are solved in Radix or Floating UI. Hand-rolling requires ref-juggling and global listeners. Adopt battle-tested primitives to reduce complexity.
2. **Co-locate the contract.** The `data-overlay-content` marker and document-level listeners split logic across files. Use a compound component (e.g., `<SelectableSurface>`) to own both the scroll area and menu via context. Replace DOM marking with component composition.
3. **Use a stack, not arbitration.** The `Escape`, `stopImmediatePropagation`, and `defaultPrevented` dance happens when listeners compete. Use a modal/focus stack where only the topmost layer receives `Escape`. Standard `<Dialog>` primitives provide this.
4. **Make state explicit.** Replace `openedBySelectionRef`, `touchActive`, and interleaved `selectionchange`/`touchend` with a named enum (`idle` | `armed` | `open`) and a reducer. Consolidates implicit transitions across scattered listeners into one readable table.
5. **Split desktop and mobile.** Unifying right-click and selection-then-touch creates timing issues. Use two distinct, narrow hooks composed by the surface instead of one complex, generalized hook.

**Meta-principle:** Boundary complexity (DOM and event system) evades type-checking and unit tests. Pulling boundaries into a single owner (component or library) converts distributed contracts into local implementation details.
