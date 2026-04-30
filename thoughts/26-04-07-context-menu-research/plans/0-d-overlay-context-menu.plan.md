---
name: Abstract: Overlay Context Menu Plan
last_updated: 2026-04-28 15:23, 7bf2b9f
---

# Abstract: Overlay Context Menu Plan

Original design for the context menu.

## Core Architecture
- `useOverlayContextMenu.js` handles state and close-on-Escape logic (`e.stopPropagation()` when menu is open to prevent `BaseOverlay` from closing).
- `OverlayContextMenu.jsx` renders via `createPortal(..., document.body)` at `z-[150]`.
