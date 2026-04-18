---
last_updated: 2026-04-18 16:38, 21e505e
---
# Finalized Plan: Overlay Context Menu (Zen + Digest)

## Scope

Implement a shared right-click context menu for overlay reading surfaces only:
- `ZenModeOverlay` in `client/src/components/ZenModeOverlay.jsx`
- `DigestOverlay` in `client/src/components/DigestOverlay.jsx`

### Out of Scope
- No card/feed-level context menu.
- No touch long-press custom menu.
- No changes to lock ownership (`client/src/lib/zenLock.js` behavior stays intact).
- No changes to pull-to-close / overscroll gesture hooks.

## Current State Analysis

- `ZenModeOverlay` and `DigestOverlay` render through `BaseOverlay.jsx`, which owns the shared portal-based full-screen layout and gesture hooks.
- Neither overlay handles `onContextMenu`; browser default context menu currently appears on right click.
- Overlay exclusivity is controlled by `acquireZenLock`/`releaseZenLock` in `client/src/lib/zenLock.js`.
- Touch gestures are implemented with specific listeners on overlay container/scroll nodes.

## Desired End State

Right-clicking within summary/digest prose opens a project-owned context menu with consistent options and positioning in both overlays. Menu lifecycle remains local to each overlay and closes on outside click, Escape, and overlay close. Existing pull-to-close/overscroll gestures and overlay locking behavior continue unchanged.

## Implementation Plan

### Phase 1: Shared Overlay Context Menu Primitive

#### 1. Add hook for menu state and close lifecycle
**File**: `client/src/hooks/useOverlayContextMenu.js` (new)

Implement a hook with:
- state: `isOpen`, `anchorX`, `anchorY`, `contextPayload`
- exposure of `handleContextMenu(event, payload)` and `closeMenu()`
- open-state lifecycle handlers:
  - `pointerdown` outside handler closes menu.
  - `keydown` Escape arbitration: When menu is open and Escape is pressed, close menu and `e.stopPropagation()` to stop that Escape from cascading into overlay-close for that same key event.

#### 2. Add presentational menu component
**File**: `client/src/components/OverlayContextMenu.jsx` (new)

Implement a presentational component:
- Render menu via `createPortal(..., document.body)`.
- Accept absolute anchor coordinates and action callbacks.
- Layered above overlay (`z-[150]`).
- Minimal action set for first pass (only actions already aligned with existing overlay affordances, e.g. close, open original link).

### Phase 2: Overlay Integration

#### 1. Zen integration
**File**: `client/src/components/ZenModeOverlay.jsx`

Inside `ZenModeOverlay`:
- use `useOverlayContextMenu`
- thread `onContextMenu` through `ZenModeOverlay` into the shared `BaseOverlay` scroll/content surface (explicitly target the `scrollRef` content area).
- render `OverlayContextMenu`
- ensure menu state resets on overlay close/unmount.

#### 2. Digest integration
**File**: `client/src/components/DigestOverlay.jsx`

Mirror the same pattern as Zen:
- same attach point semantics through `BaseOverlay` (`scrollRef` area)
- same Escape arbitration behavior
- same close/unmount cleanup

### Keep lock and gesture systems untouched
**Files**:
- `client/src/hooks/useSummary.js`
- `client/src/hooks/useDigest.js`
- `client/src/lib/zenLock.js`
- `client/src/hooks/usePullToClose.js`
- `client/src/hooks/useOverscrollUp.js`

**Changes**:
- No direct logic changes expected; verify unchanged behavior under menu interactions.

## Acceptance Criteria

### Automated
- [ ] `cd client && npm run build`

### Manual
- [ ] Right-click in Zen prose opens custom menu at cursor location.
- [ ] Right-click in Digest prose opens same menu behavior.
- [ ] Outside click closes menu.
- [ ] First Escape closes menu only; subsequent Escape closes overlay.
- [ ] Text selection/link interaction remains normal.
- [ ] Pull-to-close and overscroll-up gestures still behave identically to current behavior.
- [ ] No lock regressions (single overlay open at a time still enforced).