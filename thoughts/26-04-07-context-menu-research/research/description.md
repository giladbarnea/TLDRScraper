---
date: 2026-04-08
topic: "Custom Context Menu in Zen/Digest Overlays"
status: complete
last_updated: 2026-04-08 10:22, 38b11fd
---
# Research: Custom Context Menu in Zen/Digest Overlays

## Executive Summary
Zen and Digest overlays are rendered as full-screen portals with nearly identical header/content structure and mobile-first touch gesture hooks. Neither overlay currently handles `onContextMenu`, and there is no global contextmenu interception in `client/src/`. Right-click interactions are therefore left to browser default behavior. For cards, `useLongPress` explicitly ignores non-primary mouse buttons, so right-click does not enter select mode. A custom context menu should be implemented as a shared overlay-level interaction primitive used by both `ZenModeOverlay` and `DigestOverlay`, while preserving existing pull-to-close and overscroll-to-complete touch gestures.

## Detailed Findings

### Overlay Rendering and Interaction Surface
**Files**:
- `client/src/components/ArticleCard.jsx`
- `client/src/components/DigestOverlay.jsx`
- `client/src/hooks/usePullToClose.js`
- `client/src/hooks/useOverscrollUp.js`
- `client/src/hooks/useScrollProgress.js`

**Mechanism**:
- `ZenModeOverlay` is defined inside `ArticleCard.jsx` and rendered with `createPortal(..., document.body)` as `fixed inset-0 z-[100]`. It contains:
  - Header with close button, domain link, mark-consumed action.
  - Scrollable content area using `dangerouslySetInnerHTML` for rendered summary HTML.
  - Pull-to-close hook bound to container/scroll refs.
  - Overscroll-up hook bound to scroll ref for bottom pull completion gesture.
- `DigestOverlay` duplicates this layout and gesture pattern, also in a portal at `z-[100]` with similar close/mark-consumed controls and markdown HTML rendering.
- Both overlays install `Escape` close handling and set `document.body.style.overflow = 'hidden'` while open.

### Open/Close Ownership and Mutual Exclusion
**Files**:
- `client/src/hooks/useSummary.js`
- `client/src/hooks/useDigest.js`
- `client/src/App.jsx`

**Mechanism**:
- `useSummary` owns a module-level singleton lock (`zenLockOwner`) exposed via `acquireZenLock`/`releaseZenLock`.
- Single-article summary overlay opens only when lock acquisition succeeds for owner `url`.
- `useDigest` imports the same lock helpers and opens digest only when lock acquisition succeeds for owner `'digest'`.
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
- `client/src/components/ArticleCard.jsx`

**Mechanism**:
- `useLongPress` exits early for mouse non-primary buttons (`if (e.pointerType === 'mouse' && e.button !== 0) return`), so right-click is currently ignored by long-press logic.
- There is no existing `onContextMenu` handler in `client/src`, so native browser context menu appears where supported.
- Overlay content containers currently do not intercept right-click, and there is no shared custom context menu component/state machine.

## Architecture & Patterns
- Portal-first overlays: both Zen and Digest render to `document.body` and own their own scroll/gesture surfaces.
- Shared lock across independent hooks: `useDigest` reuses lock ownership from `useSummary` to enforce exclusivity.
- Gesture-first mobile interactions: pull-to-close and overscroll-complete are touch event listeners on overlay container/scroll elements.
- Localized open/close commands: each overlay controls its own close semantics and lifecycle side effects.

## Open Questions / Risks
- [ ] **Event conflict risk**: Adding pointer/mouse handlers for custom context menu in overlay content may interfere with touch gesture hooks if listeners are attached too high in the DOM tree.
- [ ] **Selection-in-prose risk**: Custom context menu should avoid blocking text selection and link opening inside rendered prose.
- [ ] **Consistency risk**: Duplicated Zen/Digest overlay structures can drift; implementing context menu in one component only creates behavior mismatch.
- [ ] **Layering risk**: Context menu portal z-index must be above overlay (`z-[100]`) and toast layer (`z-[300]`) if interaction priority requires it.

## Concrete Integration Points
1. Add a shared hook/component pair (e.g., `useOverlayContextMenu` + `OverlayContextMenu`) that:
   - Tracks anchor position and menu visibility.
   - Handles `onContextMenu` (desktop) and optional long-press fallback inside overlay content area.
   - Closes on outside click, Escape, and overlay close.
2. Attach the handler to both overlay content roots:
   - `ZenModeOverlay` scroll/content wrapper.
   - `DigestOverlay` scroll/content wrapper.
3. Keep lifecycle ownership unchanged:
   - Do **not** alter `zenLockOwner` semantics.
   - Menu visibility should be ephemeral UI state inside each overlay and reset on close.
4. Ensure touch gestures remain authoritative:
   - Do not install blocking non-passive touch listeners beyond existing pull/overscroll hooks.
   - Limit context-menu interception to mouse/right-click path unless explicitly adding long-press behavior.
