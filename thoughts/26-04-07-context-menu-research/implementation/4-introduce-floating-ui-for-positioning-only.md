---
name: Abstract: Introduce Floating UI For Positioning Only
last_updated: 2026-04-28 15:22
---

# Abstract: Introduce Floating UI For Positioning Only

Replaces custom viewport math with `@floating-ui/react-dom@2.1.8`.

## Key Changes
- `OverlayContextMenu.jsx` uses `useFloating` initialized with `strategy: 'fixed'`, `transform: false`, and `autoUpdate`.
- `useOverlayContextMenu.js` produces a `positionReference` object (point or range) for `OverlayContextMenu` to consume.
- `setMenuNode` callback ref combines `menuRef.current` (needed by `useOverlayMenuDismissal`) and `floatingRefs.setFloating` (needed by FUI).
- Interaction primitives (Escape, focus, outside-click) remain manually wired.
