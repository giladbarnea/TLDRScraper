---
name: state-machines/tracked-state
description: Internal utility state machine for tracked values in gestures.
last_updated: 2026-05-02 11:36
---
# State Machines: Tracked State

### 17. Tracked State

| | |
|---|---|
| **Pattern** | `useState` + `useRef` sync via callback setter |
| **File** | `hooks/useTrackedState.js` |
| **Scope** | Internal utility for gesture hooks |

#### Purpose

Gesture hooks (`usePullToClose`, `useOverscrollUp`) need to read the current state value inside event handlers that fire after state updates. Normal `useState` + `useRef` requires a separate `useEffect` to sync the ref after each render. `useTrackedState` encapsulates this pattern.

#### API

```js
useTrackedState(initialValue) → [value, setTrackedValue, valueRef]
```

| Return | Type | Description |
|---|---|---|
| `value` | T | React state value |
| `setTrackedValue` | (T | (prev: T) => T) => void | Setter that updates both state and ref |
| `valueRef` | { current: T } | Ref that stays in sync with state |

#### Implementation

The setter uses `useCallback` with a functional state update. Inside the update, it resolves the new value (handling both direct values and updater functions) and writes it to `valueRef.current` before returning.

#### Consumers

- `usePullToClose`: Tracks `pullOffset` for threshold check in `handleTouchEnd`
- `useOverscrollUp`: Tracks `overscrollOffset` for threshold check in `handleTouchEnd`

---
