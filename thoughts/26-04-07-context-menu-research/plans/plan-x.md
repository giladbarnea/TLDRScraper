---
last_updated: 2026-04-08 19:29, e1aaa72
---
# Custom Context Menu in Zen/Digest Overlays Implementation Plan

## Overview

Implement a shared custom context menu interaction that works consistently in both Zen and Digest overlays without disrupting existing overlay lock semantics or mobile touch gestures.

## Current State Analysis

- `ZenModeOverlay` in `ArticleCard.jsx` and `DigestOverlay` in `DigestOverlay.jsx` use near-identical portal-based full-screen layouts with shared gesture hooks (`usePullToClose`, `useOverscrollUp`, `useScrollProgress`).
- Neither overlay handles `onContextMenu`; browser default context menu currently appears on right click.
- Overlay exclusivity is controlled by `acquireZenLock`/`releaseZenLock` shared between `useSummary` and `useDigest`; this flow must remain unchanged.
- Existing long-press behavior (`useLongPress`) explicitly ignores non-primary mouse buttons, so right-click is currently not captured by that path.

## Desired End State

Right-clicking within summary/digest prose opens a project-owned context menu with consistent options and positioning in both overlays. Menu lifecycle remains local to each overlay and closes on outside click, Escape, and overlay close. Existing pull-to-close/overscroll gestures and overlay locking behavior continue unchanged.

### Key Discoveries:
- Overlay structures are intentionally parallel, so introducing context menu in only one overlay would create UX drift.
- Lock semantics are centralized and already shared across summary and digest overlays; context-menu state should stay local and not touch lock ownership.
- Touch gestures are implemented with specific non-passive listeners on overlay container/scroll nodes; new context-menu handling should avoid adding competing touch interception.

## What We're NOT Doing

- No changes to digest/single-summary generation APIs.
- No redesign of selection dock or card-level long-press behavior.
- No changes to overlay lock acquisition/release (`zenLockOwner`) semantics.
- No global document-wide context menu override outside the two overlays.

## Implementation Approach

Add a reusable overlay-scoped context-menu primitive (hook + component) and wire it into both overlay content roots. Keep handlers mouse/contextmenu-first for this effort, leaving mobile long-press custom menu out-of-scope to avoid gesture conflicts.

## Phase 1: Shared Overlay Context Menu Primitive

### Overview
Introduce a shared hook/component pair that manages open position, close mechanics, and menu actions.

### Changes Required:

#### 1. Add hook for menu state and close lifecycle
**File**: `client/src/hooks/useOverlayContextMenu.js`
**Changes**:
- Add a hook that stores `{isOpen, x, y, contextPayload}`.
- Expose `handleContextMenu(event, payload)`, `closeMenu()`, and `menuProps`.
- Register cleanup listeners while open:
  - `pointerdown` outside handler.
  - `keydown` Escape handler.
- Ensure all listeners are removed on unmount and on close.

```js
useOverlayContextMenu()
  -> onContextMenu(event, payload)
  -> closeMenu()
  -> return { isOpen, anchor, payload, handlers }
```

#### 2. Add presentational menu component
**File**: `client/src/components/OverlayContextMenu.jsx`
**Changes**:
- Render menu via `createPortal(..., document.body)`.
- Accept absolute anchor coordinates and action callbacks.
- Keep z-index above overlay and toast stack where required.
- Provide keyboard-focusable actions and dismiss affordances.

```jsx
OverlayContextMenu({ anchorX, anchorY, onClose, actions })
```

### Success Criteria:

#### Automated Verification:
- [ ] `cd client && npm run build`

#### Manual Verification
- [ ] Right-click in summary overlay prose opens custom menu at cursor location.
- [ ] Right-click in digest overlay prose opens same menu behavior.
- [ ] Escape closes menu without closing overlay.
- [ ] Clicking outside menu closes it.
- [ ] No regressions in pull-to-close and overscroll-complete gestures on touch devices.

**Implementation Note**: After completing this phase and passing automated checks, pause for manual validation before any additional scope.

---

## Phase 2: Integrate with Zen and Digest Overlays

### Overview
Wire the shared primitive into both overlay components in a way that preserves existing close/mark-consumed flows.

### Changes Required:

#### 1. Wire into `ZenModeOverlay`
**File**: `client/src/components/ArticleCard.jsx`
**Changes**:
- Instantiate shared context-menu hook inside `ZenModeOverlay`.
- Attach `onContextMenu` to prose container or a dedicated overlay content wrapper (not top-level container).
- Define action set aligned with overlay affordances (e.g., open original link, mark consumed, close menu).
- Reset menu state on overlay close/unmount.

```jsx
<contentWrapper onContextMenu={handleOverlayContextMenu}>
  <OverlayContextMenu ... />
</contentWrapper>
```

#### 2. Wire into `DigestOverlay`
**File**: `client/src/components/DigestOverlay.jsx`
**Changes**:
- Mirror the same integration pattern used in `ZenModeOverlay`.
- Use digest-specific action callbacks where needed (e.g., close digest via existing `onClose`, mark consumed via `onMarkRemoved`).
- Keep behavior parity with summary overlay.

#### 3. Keep lock and gesture systems untouched
**Files**:
- `client/src/hooks/useSummary.js`
- `client/src/hooks/useDigest.js`
- `client/src/hooks/usePullToClose.js`
- `client/src/hooks/useOverscrollUp.js`

**Changes**:
- No direct logic changes expected; verify unchanged behavior under menu interactions.

### Success Criteria:

#### Automated Verification:
- [ ] `cd client && npm run build`

#### Manual Verification
- [ ] Summary overlay still opens/closes through existing flows and lock behavior.
- [ ] Digest overlay still opens/closes through existing flows and lock behavior.
- [ ] Context menu does not block text selection or link interactions unexpectedly.
- [ ] Context menu does not trigger while using touch pull-to-close / overscroll gestures.
- [ ] Toast interactions and overlay layering remain visually correct.

**Implementation Note**: Pause after this phase for human confirmation of manual checks.

---

## Testing Strategy

### Unit Tests:
- Hook behavior tests for open/close transitions and cleanup of global listeners.
- Component tests for rendering at provided coordinates and action callback firing.

### Integration Tests:
- Overlay-level integration tests validating menu attach points in both `ZenModeOverlay` and `DigestOverlay`.
- Lock lifecycle smoke tests ensuring `acquireZenLock`/`releaseZenLock` behavior is unaffected by menu open/close.

### Manual Testing Steps:
1. Open a summary overlay, right-click prose, run each menu action.
2. Open digest overlay, verify same menu open/close and actions.
3. Test Escape and outside-click dismissal.
4. On touch device/emulation, verify pull-to-close and overscroll-complete still work naturally.
5. Verify no console errors during rapid open/close of overlay + menu.

## References

- Requirements and scope input: `thoughts/26-04-07-context-menu-research/research/description.md`
- Supporting research map: `thoughts/26-04-07-context-menu-research/relevant-files.md`
- Primary integration targets:
  - `client/src/components/ArticleCard.jsx`
  - `client/src/components/DigestOverlay.jsx`
  - `client/src/hooks/useSummary.js`
  - `client/src/hooks/useDigest.js`
  - `client/src/hooks/usePullToClose.js`
  - `client/src/hooks/useOverscrollUp.js`
  - `client/src/hooks/useLongPress.js`
  - `client/src/App.jsx`
