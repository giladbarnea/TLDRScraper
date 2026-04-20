---
name: Context Menu Implementation Round 1
done: 2026-04-18, 529852a7
last_updated: 2026-04-20 20:10
---
# Context Menu Implementation Round 1

## Iteration 1 Summary

"See client files abc, checked todo items in ../xyz, and doc updates 1,2,3 in files foo bar baz"

Implements context menu triggered by mobile text selection within `ZenModeOverlay`. Provides quick actions ("Close reader", "Mark done") without extra UI. Digest integration is out of scope.

## Key Changes
- **`useOverlayContextMenu.js`**: Manages state and triggers (desktop right-click, mobile text selection). Coordinates Escape key.
- **`OverlayContextMenu.jsx`**: Renders positioned portal with action buttons. Clamps to viewport. Auto-focuses first action on desktop.
- **`BaseOverlay`**: Adds `onContentContextMenu` prop. Adds `data-overlay-content` attribute to scope selection. Escape handler checks `defaultPrevented`. Disables `usePullToClose` to allow native text selection.
- **`ZenModeOverlay`**: Integrates hook and component with specific actions. `DigestOverlay` is out of scope.
- **`index.css`**: Adds `overlay-menu-enter` animation.

## Implementation Details
- **Escape key coordination**: Hook intercepts Escape in capture phase via `preventDefault()` and `stopImmediatePropagation()`. Overlay's Escape handler respects `defaultPrevented`. Single Escape closes menu, not the overlay.
- **Mobile selection**: Detected via `selectionchange`, `touchstart`, and `touchend`. Validates selection anchor sits inside `[data-overlay-content]` subtree to prevent out-of-bounds triggers.

---

## Tackling the increased complexity this iteration introduced
status::pending

The acrobatics here come from three coupling patterns, and each maps to a known principle:

**1. Stop fighting the platform.** Mobile selection menus, outside-click, focus management, positioning, ARIA — these are solved primitives in Radix / Floating UI. Most of the ref-juggling and global listeners exist because we're hand-rolling them. Adopting a primitive library is the single biggest complexity cut available, and it's what the "behemoths" actually do — they don't out-engineer the platform, they delegate to battle-tested primitives.

**2. Co-locate the contract.** The `data-overlay-content` marker + the menu's document-level listeners are "spooky action at a distance" — the contract lives in two files plus a comment block. A compound component (`<SelectableSurface>` that owns both the scroll area and the menu via context) internalizes it. The contract becomes "use this component," not "remember to mark your DOM."

**3. Use a stack, not arbitration.** The Escape `stopImmediatePropagation` + `defaultPrevented` dance exists because two listeners both want the key. A modal/focus stack where only the topmost layer sees Escape is declarative and composes. This is what `<Dialog>` primitives ship.

**4. Make the state machine explicit.** Replace `openedBySelectionRef` + `touchActive` + interleaved `selectionchange`/`touchend` with a named enum (`idle | armed | open`) and a reducer. The current code encodes transitions implicitly across four listeners; a reducer makes them one readable table.

**5. Split desktop and mobile.** They're genuinely different interaction models — one hook trying to unify right-click and selection-then-touch is what creates the timing dance. Two narrow hooks composed by the surface beat one clever general one.

The meta-principle: **complexity that lives at boundaries (DOM + event system) is the worst kind**, because it can't be type-checked or unit-tested. Pulling it into a single owner (component or library) converts "distributed contract" into "local implementation detail" — which is the move that makes big-app code feel calm despite doing more.
