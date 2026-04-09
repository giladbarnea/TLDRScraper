---
last_updated: 2026-04-09 15:10, e8d6966
---
# Finalized Plan: Overlay Context Menu (Zen + Digest)

## Decision Summary

I compared `plan-x.md` and `plan-g.md` against the co-develop adoption criteria and finalized this plan:

- Keep **plan-x** as the base (more cohesive scope boundaries, clearer verification gates).
- Cherry-pick from **plan-g** only the parts that improve precision without adding complexity:
  1. Explicit Escape arbitration rule (close menu first, overlay second).
  2. Explicit target attach point (`scrollRef` content area).
  3. Explicit z-index target (`z-[150]`) above overlay layer.
- Reject from **plan-g** anything that adds unnecessary product scope now (e.g., extra menu action exploration beyond core parity).

This yields a smaller, clearer implementation surface than either doc alone.

## Scope

Implement a shared right-click context menu for overlay reading surfaces only:
- `ZenModeOverlay` in `client/src/components/ZenModeOverlay.jsx`
- `DigestOverlay` in `client/src/components/DigestOverlay.jsx`

### Out of Scope
- No card/feed-level context menu.
- No touch long-press custom menu.
- No changes to lock ownership (`client/src/lib/zenLock.js` behavior stays intact).
- No changes to pull-to-close / overscroll gesture hooks.

## Implementation Plan

## Phase 1 — Shared Primitive

### 1) Add hook
**File**: `client/src/hooks/useOverlayContextMenu.js` (new)

Implement a hook with:
- state: `isOpen`, `anchorX`, `anchorY`
- `handleContextMenu(event)`:
  - `preventDefault()`
  - open menu at `clientX/clientY`
- `closeMenu()`
- open-state lifecycle handlers:
  - outside pointer down closes menu
  - Escape closes menu

Critical behavior:
- When menu is open and Escape is pressed, close menu and stop that Escape from cascading into overlay-close for that same key event.

### 2) Add component
**File**: `client/src/components/OverlayContextMenu.jsx` (new)

Implement a presentational component:
- Portal to `document.body`
- Positioned at captured coordinates
- Layered above overlay (`z-[150]`)
- Minimal action set for first pass (only actions already aligned with existing overlay affordances)

## Phase 2 — Overlay Integration

### 1) Zen integration
**File**: `client/src/components/ZenModeOverlay.jsx`

Inside `ZenModeOverlay`:
- use `useOverlayContextMenu`
- thread `onContextMenu` through to the shared `BaseOverlay` scroll/content surface (`scrollRef` area)
- render `OverlayContextMenu`
- ensure menu state closes on overlay close/unmount

### 2) Digest integration
**File**: `client/src/components/DigestOverlay.jsx`

Mirror the same pattern as Zen:
- same attach point semantics through `BaseOverlay`
- same Escape arbitration behavior
- same close/unmount cleanup

## Acceptance Criteria

### Automated
- [ ] `cd client && npm run build`

### Manual
- [ ] Right-click in Zen prose opens custom menu at cursor.
- [ ] Right-click in Digest prose opens same menu behavior.
- [ ] Outside click closes menu.
- [ ] First Escape closes menu only; subsequent Escape closes overlay.
- [ ] Text selection/link interaction remains normal.
- [ ] Pull-to-close and overscroll-up gestures still behave identically to current behavior.
- [ ] No lock regressions (single overlay open at a time still enforced).

## Why this is the final plan

- **Complexity check**: no global interception, no lock changes, no touch-system rewrite.
- **Quality check**: stronger than either single draft because it keeps plan-x discipline and only imports plan-g precision wins.
- **Cohesion check**: one shared primitive + symmetric integration in both overlays, no drift.
