---
name: Abstract: Split Desktop and Mobile Overlay Menu Paths
last_updated: 2026-04-28 15:22
---

# Abstract: Split Desktop and Mobile Overlay Menu Paths

Behavior-preserving refactor of `useOverlayContextMenu.js`.

## Key Changes
- Replaced `openedBySelectionRef` with `source` field on menu state (`MenuOpenSource` enum).
- `menuStateRef` and synchronous `setMenuState` pattern introduced so dismissal paths read the correct `source` before native-selection clears.
- `useOverlayMenuDismissal` isolated as the sole owner of outside pointerdown and Escape arbitration.
