---
date: 2026-04-07
topic: "Custom Context Menu in Zen/Digest Overlays"
status: complete
last_updated: 2026-04-08 08:29, f1aa954
---
# Context Menu in Zen/Digest Overlays — Relevant Files
 
## `client/src/components/ArticleCard.jsx`
Contains `ZenModeOverlay` (inline component, lines ~26–132). Renders via `createPortal` to `document.body` at `z-[100]`. Has a fixed header (close button, domain link, mark-removed button, progress bar) and a scrollable content area with `.prose` + `dangerouslySetInnerHTML`. Uses `pull-to-close`, `overscroll-to-dismiss`, and `scroll-progress` hooks.
 
## `client/src/components/DigestOverlay.jsx`
Standalone component, nearly identical structure to `ZenModeOverlay`. Rendered via `createPortal` in `App.jsx`. Controlled by `useDigest`. Header shows article count.
 
## `client/src/hooks/useSummary.js`
Owns the zen-lock singleton (`zenLockOwner`, `acquireZenLock`, `releaseZenLock`) — a module-level guard ensuring only one overlay is open at a time. Also owns summary fetch state and `expanded` open/close state.
 
## `client/src/hooks/useDigest.js`
Controls digest overlay open/close state, parallel to `useSummary`. Participates in the same zen-lock mechanism.
 
## `client/src/hooks/useLongPress.js`
Explicitly ignores non-primary mouse buttons (`e.button !== 0` guard on `pointerdown`). No right-click / context menu handling exists anywhere in the codebase.
 
## `client/src/App.jsx`
Renders `DigestOverlay` via portal. Entry point for digest overlay lifecycle wiring.