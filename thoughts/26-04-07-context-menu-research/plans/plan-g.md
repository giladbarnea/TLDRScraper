---
last_updated: 2026-04-08 19:29, e1aaa72
---
# Context Menu Implementation Plan

## Overview
Implement a shared custom context menu (right-click) for both `ZenModeOverlay` and `DigestOverlay`. Currently, no custom context menu exists, and browser default behavior is used. The goal is to provide a consistent custom context menu for these overlays without interfering with the existing touch gestures (pull-to-close, overscroll-up) or the `zenLockOwner` exclusivity mechanism.

## Current State Analysis
- Both `ZenModeOverlay` (in `ArticleCard.jsx`) and `DigestOverlay` (in `DigestOverlay.jsx`) render as `fixed inset-0 z-[100]` portals attached to `document.body`.
- They share a common structure: a fixed header and a flex-1 scrolling content area (`<div ref={scrollRef}>`).
- Touch gestures (pull-to-close, overscroll-up) are bound to the `containerRef` and `scrollRef` respectively.
- `useLongPress` explicitly ignores non-primary mouse buttons (`e.button !== 0`), meaning right-clicks are ignored by cards.
- There is no existing `onContextMenu` handler in `client/src/`.
- `useSummary` and `useDigest` share a singleton lock (`zenLockOwner`) to ensure only one overlay is open at a time.

### Key Discoveries:
- **Event Scoping:** The `onContextMenu` handler should be attached to the scrolling content container (`<div ref={scrollRef}>`), not the entire document or overlay container, to explicitly target the reading area.
- **Z-Index:** The context menu needs a z-index higher than the overlays (`z-[100]`), e.g., `z-[150]`.
- **Exclusivity:** The context menu must be localized (ephemeral state within the overlay component itself) so it naturally unmounts when the overlay closes.
- **Escape Key Handling:** Both overlays currently listen for `Escape` to close themselves. If the context menu is open, pressing `Escape` should close the menu but *not* the overlay. This requires `e.stopPropagation()` when the menu handles the keydown, or conditional logic in the overlay's escape handler.

## What We're NOT Doing
- We are NOT implementing custom context menus for the main feed/article cards (sticking strictly to the overlays as per research).
- We are NOT modifying the `zenLockOwner` mechanism. The context menu will be internal state to the overlays.
- We are NOT adding long-press fallback for touch devices (unless it organically fits a cross-platform pointer approach, but the focus is right-click context menu).
- We are NOT blocking standard text selection in the prose area.

## Implementation Approach
1. Create a `useOverlayContextMenu` hook to manage the state (isOpen, x, y coordinates) and behavior (open, close, positioning, click-outside, escape to close) of the context menu.
2. Create an `OverlayContextMenu` component to render the menu visually at the captured coordinates.
3. Integrate the hook and component into both `ZenModeOverlay` and `DigestOverlay`.

## Phase 1: Shared Hook and Component

### Overview
Build the isolated, reusable logic and UI for the context menu.

### Changes Required:

#### 1. Context Menu Hook
**File**: `client/src/hooks/useOverlayContextMenu.js` (NEW)
**Changes**:
- Create a hook that maintains `{ isOpen, x, y }` state.
- Return a `handleContextMenu` function to bind to elements (`e.preventDefault()`, set coordinates based on `e.clientX`/`e.clientY`, set `isOpen: true`).
- Return a `closeMenu` function.
- Add an effect to handle global `click` (to close on outside click) and global `keydown` (to close on `Escape` and call `e.stopPropagation()` if the menu was open, preventing the parent overlay from closing simultaneously).

```javascript
// client/src/hooks/useOverlayContextMenu.js
export function useOverlayContextMenu() {
  // state: isOpen, position (x,y)
  // handleContextMenu: prevents default, sets pos, opens
  // closeMenu: resets state
  // useEffect: listens for click (closeMenu) and keydown (Escape -> closeMenu + stopPropagation)
  return { isOpen, position, handleContextMenu, closeMenu };
}
```

#### 2. Context Menu Component
**File**: `client/src/components/OverlayContextMenu.jsx` (NEW)
**Changes**:
- Create a presentational component that renders an absolutely positioned `ul` (or `div` with `role="menu"`) at the given `x` and `y` coordinates.
- Set `z-index` to `z-[150]`.
- Accept `children` or `items` (array of actions) to render the menu items.
- Ensure styling matches the application (e.g., bg-white, shadow-elevated, rounded-lg, text-slate-700).

```javascript
// client/src/components/OverlayContextMenu.jsx
export function OverlayContextMenu({ isOpen, position, onClose, children }) {
  if (!isOpen) return null;
  // render fixed/absolute div at position.x, position.y
  // handle portal rendering if necessary, but standard absolute inside the fixed overlay should work since it's already z-[100]
}
```

### Success Criteria:
#### Manual Verification
- [ ] Hook correctly captures coordinates and toggles state.
- [ ] Component renders visually correctly at specified coordinates.

---

## Phase 2: Integration into Overlays

### Overview
Wire the shared hook and component into the existing `ZenModeOverlay` and `DigestOverlay` components.

### Changes Required:

#### 1. Integrate into ZenModeOverlay
**File**: `client/src/components/ArticleCard.jsx`
**Changes**:
- Import `useOverlayContextMenu` and `OverlayContextMenu`.
- Initialize `const { isOpen, position, handleContextMenu, closeMenu } = useOverlayContextMenu();` inside `ZenModeOverlay`.
- Attach `onContextMenu={handleContextMenu}` to the `<div ref={scrollRef} ...>` element.
- Render `<OverlayContextMenu>` as a sibling to the content inside the overlay container.
- For the menu items, add relevant actions (e.g., "Copy Text", "Close Overlay"). *Note: Exact actions aren't specified in research, so basic placeholder or standard actions will be implemented, specifically a "Close" action to mirror the header.*
- Ensure the overlay's native escape listener does not fire if the context menu's escape listener caught the event (handled by the hook's stopPropagation, or by checking `if (isOpen) return;` in the overlay's escape handler).

#### 2. Integrate into DigestOverlay
**File**: `client/src/components/DigestOverlay.jsx`
**Changes**:
- Apply the exact same integration pattern as `ZenModeOverlay`.
- Import hook and component.
- Attach `onContextMenu` to `<div ref={scrollRef} ...>`.
- Render the menu component.

### Success Criteria:

#### Manual Verification
- [ ] Right-clicking the content area of a Zen summary opens the custom context menu at the mouse cursor.
- [ ] Native browser context menu does *not* appear.
- [ ] Clicking outside the custom menu closes it.
- [ ] Pressing `Escape` when the menu is open closes *only* the menu, not the underlying overlay.
- [ ] Right-clicking in the Digest overlay works identically.
- [ ] Normal text selection in the prose area continues to work.
- [ ] Pull-to-close and overscroll-up gestures remain fully functional and unaffected.

## Testing Strategy

### Manual Testing Steps:
1. Open a Zen summary. Right-click on the paragraph text. Verify custom menu appears.
2. Verify native context menu is suppressed.
3. Left-click elsewhere. Verify custom menu dismisses.
4. Right-click to open menu again. Press `Escape`. Verify menu dismisses, but overlay remains open.
5. Press `Escape` again. Verify overlay closes.
6. Select text with left click and drag. Verify selection works properly.
7. Repeat steps 1-6 for the Digest overlay.
8. Test touch gestures (pull down, overscroll up) using browser devtools mobile emulation to ensure no regression.

## References
- Research: `thoughts/26-04-07-context-menu-research/research/description.md`
- Relevant Files: `thoughts/26-04-07-context-menu-research/relevant-files.md`
