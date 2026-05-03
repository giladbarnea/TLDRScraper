---
name: client/gestures
description: Client-side gesture handling, specifically swipe-to-remove.
last_updated: 2026-05-02 11:36
---
# Client: Gestures

[→ State Machines: Interaction & Gestures](../state-machines/interaction-and-gestures.md)

## Gesture / Swipe-to-Remove (Domain D)

Swipe-to-remove gesture state (`idle` → `dragging` → `error`) is managed via a per-article reducer. See [State Machines: Interaction and Gestures](../state-machines/interaction-and-gestures.md#4-gesture-swipe-to-remove) for the state machine specification.

**Key modules:** `reducers/gestureReducer.js`, `hooks/useSwipeToRemove.js`

---
