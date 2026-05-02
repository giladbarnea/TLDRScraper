---
last_updated: 2026-05-02 10:48
---

# Client: Gestures

[→ State Machines: Interaction & Gestures](../state-machines/interaction-and-gestures.md)

## Gesture / Swipe-to-Remove (Domain D)

Swipe-to-remove gesture state (`idle` → `dragging` → `error`) is managed via a per-article reducer. See [STATE_MACHINES.md](STATE_MACHINES.md#4-gesture-swipe-to-remove) for the state machine specification.

**Key modules:** `reducers/gestureReducer.js`, `hooks/useSwipeToRemove.js`

---
