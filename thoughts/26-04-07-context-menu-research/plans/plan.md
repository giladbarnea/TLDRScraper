---
last_updated: 2026-04-18 12:17
---
# Context Menu in Zen/Digest Overlays Implementation Plan

## Overview
Implement a shared custom context menu (right-click) for both `ZenModeOverlay` and `DigestOverlay`. Currently, no custom context menu exists within the overlays, and the browser's default behavior is used. The goal is to provide a consistent custom context menu without interfering with the existing touch gestures (pull-to-close, overscroll-up) or the shared `zenLockOwner` exclusivity mechanism.

## Current State Analysis
- `ZenModeOverlay` (in `client/src/components/ZenModeOverlay.jsx`) and `DigestOverlay` (in `client/src/components/DigestOverlay.jsx`) render through `BaseOverlay.jsx`, which is a `fixed inset-0 z-[100]` portal attached to `document.body`.
- They share a common structure: a fixed header and a flex-1 scrolling content area (`<div ref={scrollRef}>`) owned by `BaseOverlay`.
- Touch gestures (pull-to-close, overscroll-up) are bound to the `containerRef` and `scrollRef` respectively.
- `useLongPress` explicitly ignores non-primary mouse buttons (`e.button !== 0`), meaning right-clicks are ignored by elements using it.
- There is no existing `onContextMenu` handler in `client/src/`.
- `useSummary` and `useDigest` share a singleton lock from `client/src/lib/zenLock.js` to ensure only one overlay is open at a time.

### Key Discoveries:
- **Event Scoping:** The `onContextMenu` handler should be attached to the scrolling content container (`<div ref={scrollRef}>`) in `BaseOverlay`, not the entire document or overlay container, to explicitly target the reading area.
- **Z-Index:** The context menu needs a z-index higher than the overlays (`z-[100]`), e.g., `z-[150]`.
- **Exclusivity:** The context menu must be localized (ephemeral state within the overlay component itself) so it naturally unmounts when the overlay closes.
- **Escape Key Arbitration Rule:** Both overlays currently listen for `Escape` to close themselves. If the context menu is open, pressing `Escape` must close the menu first, but *not* the underlying overlay. This requires the menu to intercept the keydown and call `e.stopPropagation()`.

## Out of Scope
- No custom context menu for the main feed/article cards.
- No modifications to the `zenLockOwner` mechanism in `client/src/lib/zenLock.js`.
- No long-press fallback for touch devices (staying focused on the right-click desktop experience).
- No blocking of standard text selection in the prose area.

## Implementation Approach

### Phase 1: Shared Primitive

#### 1) Add Context Menu Hook
**File**: `client/src/hooks/useOverlayContextMenu.js` (NEW)

Implement an isolated hook that manages:
- **State**: `isOpen`, `anchorX`, `anchorY`.
- **`handleContextMenu(event)`**:
  - Calls `e.preventDefault()`.
  - Sets coordinates based on `e.clientX`/`e.clientY` and opens the menu.
- **`closeMenu()`**: Resets state to closed.
- **Open-state Lifecycle Handlers (via `useEffect`)**:
  - Global `pointerdown` / `click` outside closes the menu.
  - Global `keydown` for `Escape` closes the menu and must call `e.stopPropagation()` to prevent the parent overlay from simultaneously closing.

#### 2) Add Context Menu Component
**File**: `client/src/components/OverlayContextMenu.jsx` (NEW)

Implement a presentational component:
- Renders via portal to `document.body`.
- Positioned absolutely at the captured `anchorX` and `anchorY` coordinates.
- Set `z-index` to `z-[150]`, putting it above the `z-[100]` `BaseOverlay`.
- Receives a minimal action set (actions already aligned with existing overlay affordances, like closing the overlay).

### Phase 2: Integration into Overlays

#### 1) ZenModeOverlay Integration
**File**: `client/src/components/ZenModeOverlay.jsx`

Inside `ZenModeOverlay`:
- Initialize `useOverlayContextMenu`.
- Pass the `onContextMenu` handler down to the shared `BaseOverlay` to target the `scrollRef` content area.
- Render `<OverlayContextMenu>` component.
- Ensure menu state is naturally reset/cleaned up if the overlay unmounts.

#### 2) DigestOverlay Integration
**File**: `client/src/components/DigestOverlay.jsx`

Inside `DigestOverlay`:
- Apply the exact same integration pattern as `ZenModeOverlay`.
- Target the same attach point semantics through `BaseOverlay`.
- Keep the same Escape arbitration and close/unmount cleanup behavior.

## Acceptance Criteria

### Automated
- [ ] Code builds without errors (`cd client && npm run build`).

### Manual
- [ ] Right-clicking inside ZenModeOverlay's prose opens the custom menu at the cursor.
- [ ] Right-clicking inside DigestOverlay's prose opens the same custom menu.
- [ ] The native browser context menu is completely suppressed in these areas.
- [ ] Clicking outside the custom menu closes it.
- [ ] Pressing `Escape` when the menu is open closes *only* the menu, leaving the underlying overlay open.
- [ ] Pressing `Escape` when the menu is closed closes the overlay as expected.
- [ ] Standard text selection and link interaction remain functional.
- [ ] Pull-to-close and overscroll-up gestures remain identical to current behavior.
- [ ] Overlay lock exclusivity (`zenLock.js`) continues to function with zero regressions.