---
name: Abstract: Split Desktop and Mobile Overlay Menu Paths Implementation Plan
last_updated: 2026-04-28 15:23, 7bf2b9f
---

# Abstract: Split Desktop and Mobile Overlay Menu Paths Implementation Plan

Extracts internal paths in `useOverlayContextMenu.js` to separate owners.

## Relevant Context
- Establishes `MenuOpenSource` (`NONE`, `DESKTOP`, `MOBILE_SELECTION`).
- Isolates `useOverlayMenuDismissal` hook, which centralizes outside-pointerdown and Escape arbitration (`preventDefault()`, `stopPropagation()`, `stopImmediatePropagation()`).
- `closeMenu` receives `clearSelection` flag, driven by `menuStateRef.current.source === MOBILE_SELECTION`.
