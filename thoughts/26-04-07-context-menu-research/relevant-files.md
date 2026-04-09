---
date: 2026-04-07
topic: "Custom Context Menu in Zen/Digest Overlays"
status: complete
last_updated: 2026-04-09 15:10, e8d6966
---
# Context Menu in Zen/Digest Overlays — Relevant Files
 
## `client/src/components/ArticleCard.jsx`
Renders `ZenModeOverlay` when `summary.expanded && summary.html`. Still owns the card click/swipe/remove path that opens the single-article reading overlay.

## `client/src/components/ZenModeOverlay.jsx`
Standalone single-article overlay wrapper. Delegates the shared full-screen shell to `BaseOverlay`, passes the domain/meta header content, and renders summary HTML inside the shared prose surface.

## `client/src/components/BaseOverlay.jsx`
Owns `createPortal(..., document.body)` at `z-[100]`, the fixed header shell, the shared scrollable content area, `Escape` close handling, `document.body.style.overflow = 'hidden'`, and the shared `usePullToClose`, `useOverscrollUp`, and `useScrollProgress` hooks.
 
## `client/src/components/DigestOverlay.jsx`
Standalone digest overlay wrapper built on `BaseOverlay`. Rendered in `App.jsx`, controlled by `useDigest`, and its header shows the article count.

## `client/src/lib/zenLock.js`
Owns the zen-lock singleton (`zenLockOwner`, `acquireZenLock`, `releaseZenLock`) used to ensure only one overlay is open at a time.
 
## `client/src/hooks/useSummary.js`
Owns summary fetch state and single-article `expanded` open/close state. Imports the shared lock helpers from `client/src/lib/zenLock.js`.
 
## `client/src/hooks/useDigest.js`
Controls digest overlay open/close state, parallel to `useSummary`. Imports the same shared zen-lock helpers and participates in the same exclusivity mechanism.
 
## `client/src/hooks/useLongPress.js`
Explicitly ignores non-primary mouse buttons (`e.button !== 0` guard on `pointerdown`). No right-click / context menu handling exists anywhere in the codebase.
 
## `client/src/App.jsx`
Renders `DigestOverlay` and wires `digest.expanded`, `digest.collapse(false)`, and `digest.collapse(true)` into it.
