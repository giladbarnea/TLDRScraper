---
name: Abstract: Introduce Floating UI For Positioning Only Implementation Plan
last_updated: 2026-04-28 15:23, 7bf2b9f
---

# Abstract: Introduce Floating UI For Positioning Only Implementation Plan

Adopts `@floating-ui/react-dom` explicitly for positioning, deferring interaction primitives.

## Relevant Context
- Requires merging `menuRef.current` (used by `useOverlayMenuDismissal` for outside-pointer checking) and `floatingRefs.setFloating` via `setMenuNode`.
- Removes legacy `clampMenuPosition` logic.
- Positions via `useFloating({ strategy: 'fixed', transform: false })`.
- Upgrading to interaction primitives is left for a subsequent plan.
