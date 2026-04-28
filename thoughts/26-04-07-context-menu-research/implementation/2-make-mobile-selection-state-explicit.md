---
name: Abstract: Make Mobile Selection State Explicit
last_updated: 2026-04-28 15:23, 7bf2b9f
---

# Abstract: Make Mobile Selection State Explicit

Extracts mobile selection into `mobileSelectionMenuReducer.js`.

## Key Changes
- `client/src/reducers/mobileSelectionMenuReducer.js` owns the mobile-selection lifecycle (idle/armed/open states).
- No changes to `useOverlayMenuDismissal` or Escape arbitration.
