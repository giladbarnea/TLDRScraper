---
name: Context Menu Research
date: 2026-04-08
topic: "Custom Context Menu in Zen Overlay"
status: complete
last_updated: 2026-04-20 13:36
---
# Research: Custom Context Menu in Zen Overlay

## Executive Summary
Zen and Digest overlays are rendered as full-screen portals through a shared `BaseOverlay` shell with mobile-first touch gesture hooks. Neither overlay currently handles `onContextMenu`, and there is no global contextmenu interception in `client/src/`. Right-click interactions are therefore left to browser default behavior. For cards, `useLongPress` explicitly ignores non-primary mouse buttons, so right-click does not enter select mode. A custom context menu should be implemented as a shared overlay-level interaction primitive used by `ZenModeOverlay`, while preserving existing pull-to-close and overscroll-to-complete touch gestures. Digest overlay is considered out of scope for this research path to maintain implementation focus.

## Detailed Findings

### Overlay Rendering and Interaction Surface
**Files**:
- `client/src/components/ZenModeOverlay.jsx`
- `client/src/components/DigestOverlay.jsx`
- `client/src/components/BaseOverlay.jsx`
- `client/src/hooks/usePullToClose.js`
- `client/src/hooks/useOverscrollUp.js`
- `client/src/hooks/useScrollProgress.js`

**Mechanism**:
- `ZenModeOverlay.jsx` is now a thin wrapper that supplies single-article header content plus rendered summary HTML to `BaseOverlay`.
- `DigestOverlay.jsx` is the parallel digest wrapper that supplies the digest header and rendered digest HTML to `BaseOverlay`.
- `BaseOverlay.jsx` renders the shared `createPortal(..., document.body)` shell as `fixed inset-0 z-[100]`. It contains:
  - Header with close button, header slot, mark-consumed action, and progress bar.
  - Shared scrollable content area that renders overlay children.
  - Pull-to-close hook bound to container/scroll refs.
  - Overscroll-up hook bound to scroll ref for bottom pull completion gesture.
  - Shared `Escape` close handling and `document.body.style.overflow = 'hidden'` while open.

### Open/Close Ownership and Mutual Exclusion
**Files**:
- `client/src/hooks/useSummary.js`
- `client/src/hooks/useDigest.js`
- `client/src/lib/zenLock.js`
- `client/src/App.jsx`

**Mechanism**:
- `client/src/lib/zenLock.js` owns the module-level singleton lock (`zenLockOwner`) exposed via `acquireZenLock`/`releaseZenLock`.
- Single-article summary overlay opens only when lock acquisition succeeds for owner `url`.
- `useSummary` and `useDigest` both import the shared lock helpers.
- `useDigest` opens digest only when lock acquisition succeeds for owner `'digest'`.
- Digest overlay lifecycle is wired in `App.jsx` by passing `digest.expanded`, `digest.collapse(false)` and `digest.collapse(true)` into `DigestOverlay`.
- This lock means custom context menu UX must respect one-overlay-at-a-time assumptions; secondary modal layers inside an open overlay should not disturb lock ownership.

### Summary and Digest Completion Paths
**Files**:
- `client/src/hooks/useSummary.js`
- `client/src/lib/toastBus.js`
- `client/src/components/ToastContainer.jsx`
- `client/src/hooks/useDigest.js`

**Mechanism**:
- Summary fetch success writes markdown state and emits a toast (`emitToast`) with `onOpen: expand` callback.
- Clicking toast opens the summary overlay via lock-aware `expand`.
- Digest trigger runs async generation, updates per-article summary loading state, writes digest markdown, clears selection, and opens digest overlay.
- Digest collapse persists article lifecycle updates (mark read or removed), then releases lock.

### Right-Click and Long-Press Behavior
**Files**:
- `client/src/hooks/useLongPress.js`
- `client/src/components/ZenModeOverlay.jsx`
- `client/src/components/DigestOverlay.jsx`
- `client/src/components/BaseOverlay.jsx`

**Mechanism**:
- `useLongPress` exits early for mouse non-primary buttons (`if (e.pointerType === 'mouse' && e.button !== 0) return`), so right-click is currently ignored by long-press logic.
- There is no existing `onContextMenu` handler in `client/src`, so native browser context menu appears where supported.
- The shared overlay content surface in `BaseOverlay` currently does not intercept right-click, and there is no shared custom context menu component/state machine.

## Architecture & Patterns
- Shared overlay shell: `BaseOverlay` owns the portal, scroll surface, and gesture hooks used by both Zen and Digest wrappers.
- Shared lock across independent hooks: `useSummary` and `useDigest` both reuse lock ownership from `client/src/lib/zenLock.js` to enforce exclusivity.
- Gesture-first mobile interactions: pull-to-close and overscroll-complete are touch event listeners on overlay container/scroll elements.
- Localized open/close commands: each overlay controls its own close semantics and lifecycle side effects.

## Open Questions / Risks
- [ ] **Event conflict risk**: Adding pointer/mouse handlers for custom context menu in overlay content may interfere with touch gesture hooks if listeners are attached too high in the DOM tree.
- [ ] **Selection-in-prose risk**: Custom context menu should avoid blocking text selection and link opening inside rendered prose.
- [ ] **Consistency risk**: Zen/Digest wrapper behavior can drift around the shared `BaseOverlay`; implementing context menu in only one wrapper creates a behavior mismatch, as Digest is currently out of scope.
- [ ] **Layering risk**: Context menu portal z-index must be above overlay (`z-[100]`) and toast layer (`z-[300]`) if interaction priority requires it.

## Concrete Integration Points
1. Add a shared hook/component pair (e.g., `useOverlayContextMenu` + `OverlayContextMenu`) that:
   - Tracks anchor position and menu visibility.
   - Handles `onContextMenu` (desktop) and optional long-press fallback inside overlay content area.
   - Closes on outside click, Escape, and overlay close.
2. Attach the handler to the Zen overlay content root:
   - Thread it through `ZenModeOverlay` into the shared `BaseOverlay` scroll/content wrapper.
3. Keep lifecycle ownership unchanged:
   - Do **not** alter `client/src/lib/zenLock.js` semantics.
   - Menu visibility should be ephemeral UI state inside each overlay and reset on close.
4. Ensure touch gestures remain authoritative:
   - Do not install blocking non-passive touch listeners beyond existing pull/overscroll hooks.
   - Limit context-menu interception to mouse/right-click path unless explicitly adding long-press behavior.
