---
last_updated: 2026-02-15 07:57
---
# Summary Lifecycle Animations — Technical Spec

The animation lifecycle has two orthogonal state axes. They coexist on every card independently.

## Axis 1: Touch Phase (new, ephemeral)

Tracks the pointer lifecycle on a card. Resets between interactions. Not persisted.

```
                   pointerDown
                   [guards pass]
    ┌───────┐  ─────────────────►  ┌───────────┐
    │       │                      │           │
    │ IDLE  │  ◄────────────────── │  PRESSED  │
    │       │   move > 10px        │           │
    └───────┘   held ≥ 500ms       └─────┬─────┘
       ▲        pointerCancel            │
       │                                 │ pointerUp
       │                                 │ (< 500ms, no scroll)
       │        auto-timer               ▼
       │        (RELEASE_MS)       ┌───────────┐
       └─────────────────────────  │ RELEASED  │
                                   └───────────┘
```

Three states:

| State       | Meaning                                      | Duration             |
|-------------|----------------------------------------------|----------------------|
| `idle`      | No active touch                              | Indefinite           |
| `pressed`   | Finger is down on card, magic is stirring    | 0 – 499ms            |
| `released`  | Finger just lifted, "magic fired" burst      | Exactly RELEASE_MS   |

### Transitions

**IDLE → PRESSED** on `pointerDown`, if ALL guards pass:
- `!isSelectMode` (selection mode swallows taps for toggling)
- `!isRemoved` (removed cards handle taps differently)
- `!isDragging` (swipe gesture in progress)

If any guard fails, touch phase stays `idle`. The existing click/selection handlers proceed unaffected.

**PRESSED → IDLE** (cancellation) on any of:
- `pointerMove` exceeds 10px in either axis (user is scrolling)
- 500ms elapsed since pointerDown (long-press territory — Selectable takes over)
- `pointerCancel` (system cancelled the gesture)

**PRESSED → RELEASED** on `pointerUp`, if the press was not cancelled.

**RELEASED → IDLE** automatically, after `RELEASE_MS` (a fixed duration, ~400ms). This is a timer, not driven by any user event.

### Guards detail

The guards are evaluated once, at pointerDown. If the card's state changes mid-press (e.g. isDragging becomes true during the press), the movement-threshold cancellation handles it naturally — dragging involves pointer movement which exceeds 10px.

isSelectMode is read from `useInteraction()`. isRemoved and isDragging are from existing hooks already consumed by ArticleCard. No new data dependencies.

## Axis 2: Summary Data Status (existing)

Already implemented in `summaryDataReducer.js`. Four states:

```
  unknown ──► loading ──► available
                  │
                  └──► error
```

With `rollback` (loading → previous) and `reset` (any → unknown) edges.

No changes needed to this axis. It's the source of truth for what the card's summary data state is.

## Composite: how the two axes combine

The card's visual is a function of `(touchPhase, summaryStatus)`. The technical layer exposes both via data attributes. The visual layer (CSS/Tailwind, designed separately) targets combinations.

Key combinations:

| touchPhase | summaryStatus | What's happening                                 |
|------------|---------------|--------------------------------------------------|
| idle       | unknown       | Default card. No activity.                       |
| pressed    | unknown       | Finger down, no summary yet. "Stirring" animation. |
| released   | unknown       | Finger just lifted. Brief "fire" burst.          |
| idle       | loading       | Request in flight. "Magic line" border animation. |
| idle       | available     | Summary cached. Available indicator.             |
| idle       | error         | Fetch failed. Error state.                       |
| pressed    | available     | Finger down on a card with cached summary.       |
| released   | available     | Finger lifted, overlay about to open.            |
| pressed    | loading       | Re-tap while loading (will abort + re-fire).     |
| released   | loading       | Just re-triggered. Overlaps with ongoing loading. |

Note: `released` + `loading` happens simultaneously during the first tap-to-summarize, because onClick (which fires `fetchSummary`) runs at the same time as the RELEASED transition. See timing diagram below.

## Event flow: tap on unsummarized card

Exact sequence of events when user taps a card with `summaryStatus = 'unknown'`:

```
 t=0ms     pointerDown
           ├─ Selectable: useLongPress starts 500ms timer
           └─ Card: touchPhase = PRESSED         ◄── animation phase 1+2 starts

 t≈150ms   pointerUp (typical quick tap)
           ├─ Selectable: useLongPress timer cleared
           ├─ Card: touchPhase = RELEASED         ◄── animation phase 3 starts
           └─ Card: RELEASE_MS timer starts (400ms countdown)

 t≈150ms   click fires (same event loop turn as pointerUp, or next microtask)
           ├─ handleCardClick runs
           ├─ itemShortPress → { shouldOpenItem: true }
           ├─ summary.toggle() → fetchSummary()
           ├─ dispatchSummaryEvent(SUMMARY_REQUESTED)
           └─ summaryStatus = LOADING              ◄── "magic line" can start
                                                       (RELEASED is still active)

 t≈550ms   RELEASE_MS timer fires
           └─ touchPhase = IDLE                    ◄── phase 3 ends
               summaryStatus is still LOADING      ◄── "magic line" continues alone

 ...server processing...

 t≈5-30s   fetch response arrives
           ├─ dispatchSummaryEvent(SUMMARY_LOAD_SUCCEEDED)
           ├─ summaryStatus = AVAILABLE             ◄── "magic line" stops
           ├─ acquireZenLock → setExpanded(true)
           └─ ZenModeOverlay mounts                 ◄── overlay enters
```

The handoff from `released` to `loading` is seamless: for ~400ms after finger-up, BOTH `data-touch-phase="released"` AND `data-summary-status="loading"` are true on the DOM node. The visual layer uses this overlap to blend the "fire burst" into the "magic line."

## Event flow: tap on card with cached summary

```
 t=0ms     pointerDown → touchPhase = PRESSED
 t≈150ms   pointerUp → touchPhase = RELEASED
 t≈150ms   click → summary.toggle() → isAvailable=true → acquireZenLock → setExpanded(true)
           ZenModeOverlay mounts immediately. No fetch.
 t≈550ms   RELEASE_MS timer → touchPhase = IDLE (overlay is already open)
```

The visual layer may choose lighter animation for this case (both attributes are readable).

## Event flow: long-press (enters selection)

```
 t=0ms     pointerDown
           ├─ Selectable: useLongPress starts 500ms timer
           └─ Card: touchPhase = PRESSED         ◄── animation starts

 t=500ms   useLongPress timer fires → itemLongPress(id) → enters selection mode
           Card: auto-cancel timer fires → touchPhase = IDLE  ◄── animation stops

 t≈800ms   pointerUp
           └─ click → itemShortPress → suppressed (800ms latch) → no summary.toggle()
```

The animation plays for up to 500ms of the "pressed" phase, then cleanly cancels. No "released" burst, no request.

## Event flow: scroll cancellation

```
 t=0ms     pointerDown → touchPhase = PRESSED
 t≈80ms    pointerMove (dy > 10px, user is scrolling)
           └─ Card: touchPhase = IDLE             ◄── animation cancelled immediately
```

## The hook: `useTouchPhase`

New file: `client/src/hooks/useTouchPhase.js`

### Inputs

```js
useTouchPhase({ isSelectMode, isRemoved, isDragging })
```

All three are booleans already available in ArticleCard. No new data flows.

### Outputs

```js
{
  touchPhase,       // 'idle' | 'pressed' | 'released'
  pointerHandlers,  // { onPointerDown, onPointerMove, onPointerUp, onPointerCancel }
}
```

### Internal state

- `touchPhase` — `useState('idle')`
- `pointerIdRef` — tracks active pointer ID (reject stray pointer events)
- `startPosRef` — `{ x, y }` at pointerDown (for movement threshold)
- `cancelTimerRef` — the 500ms auto-cancel timer
- `releaseTimerRef` — the RELEASE_MS auto-clear timer

### Implementation sketch

```
onPointerDown(e):
  if guards fail → return (stay idle)
  if mouse && button !== 0 → return (only primary button)
  clear any pending release timer (handles rapid re-tap)
  record pointerId, startPos
  set touchPhase = 'pressed'
  start 500ms cancel timer → set touchPhase = 'idle'

onPointerMove(e):
  if pointerId doesn't match → return
  if touchPhase !== 'pressed' → return
  if |dx| > 10 or |dy| > 10 → clear cancel timer, set touchPhase = 'idle'

onPointerUp(e):
  if pointerId doesn't match → return
  clear cancel timer
  if touchPhase === 'pressed':
    set touchPhase = 'released'
    start RELEASE_MS timer → set touchPhase = 'idle'
  reset pointerId, startPos

onPointerCancel(e):
  if pointerId doesn't match → return
  clear cancel timer
  set touchPhase = 'idle'
  reset pointerId, startPos

cleanup (useEffect return):
  clear cancelTimer, releaseTimer
```

### Why useState, not useRef

The touch phase must trigger re-renders so the card can apply `data-touch-phase={touchPhase}` to the DOM. Three renders per tap (idle→pressed, pressed→released, released→idle) is negligible.

## Integration with ArticleCard

### Wiring the hook

```jsx
const { touchPhase, pointerHandlers } = useTouchPhase({
  isSelectMode,
  isRemoved,
  isDragging,
})
```

### Attaching handlers to the card surface

The `pointerHandlers` go on the same `<motion.div>` that has `onClick`:

```jsx
<motion.div
  {...pointerHandlers}
  onClick={handleCardClick}
  data-touch-phase={touchPhase}
  data-summary-status={summary.status}  // already exists
  // ... rest unchanged
>
```

Pointer events propagate upward. Selectable's pointer handlers on the outer div fire after the card's. No conflict — they serve different purposes (touch phase vs long-press detection) and neither calls `stopPropagation`.

### No changes to existing handlers

`handleCardClick`, `useSummary.toggle()`, `itemShortPress`, `useLongPress` — all remain exactly as-is. The touch phase hook is purely additive. It observes pointer events to produce animation state. It does not modify the interaction or summary data flows.

## Shared constants

Extract thresholds that are currently hardcoded in `useLongPress.js`:

```
client/src/lib/interactionConstants.js
```

```js
export const LONG_PRESS_THRESHOLD_MS = 500
export const POINTER_MOVE_THRESHOLD_PX = 10
export const RELEASE_DURATION_MS = 400
```

`useLongPress` imports `LONG_PRESS_THRESHOLD_MS` and `POINTER_MOVE_THRESHOLD_PX` instead of hardcoding `500` and `10`.

`useTouchPhase` imports all three.

The visual layer (CSS/Tailwind) must match `RELEASE_DURATION_MS` for its release animation duration. This is a convention coupling, documented in both places.

## Edge cases

### Rapid re-tap during RELEASED phase
pointerDown while `touchPhase === 'released'`: clear release timer, enter PRESSED. The cycle is continuous: pressed → released → pressed → released. Works naturally.

### Text selection prevents summary but release animation plays
pointerUp → RELEASED → onClick → handleCardClick detects selection → returns early. RELEASED plays its 400ms burst, then IDLE. No request fires. Acceptable: the burst is brief, and text selection while tapping is rare.

### Component unmounts during PRESSED or RELEASED
Cleanup effect clears all timers. React ignores setState calls after unmount.

### Multiple pointers (multi-touch)
The hook tracks a single `pointerIdRef`. Second finger's events don't match → ignored.

### isDragging becomes true mid-press
User starts swiping horizontally after pointerDown. Framer-motion's drag handler fires. The pointer also moves > 10px → movement threshold cancels the press → IDLE. The isDragging guard is really a pointerDown guard; mid-press cancellation is handled by movement detection.

## What this spec does NOT cover

- What the animations look like (colors, keyframes, transforms, border styles)
- How the "magic line" border animation works visually
- How the "fire burst" release animation looks
- How the "pressed/stirring" animation looks
- Whether framer-motion or CSS keyframes or both drive the animations
- How `data-touch-phase` and `data-summary-status` map to specific CSS rules

All of that belongs to the visual spec, which is a separate effort.

## Implementation notes (post-implementation)

### Files created/modified

| File | Role |
|------|------|
| `hooks/useTouchPhase.js` | The hook. Tracks pointer lifecycle, dispatches to reducer. |
| `reducers/touchPhaseReducer.js` | Pure reducer: `reduceTouchPhase(state, { type })`. Guards impossible transitions. |
| `lib/interactionConstants.js` | Shared thresholds. `useLongPress` also imports from here (was hardcoded). |
| `components/ArticleCard.jsx` | Consumes `useTouchPhase`, spreads `pointerHandlers` on `motion.div`, sets `data-touch-phase`. |

### Deviations from spec

- **Hook also accepts `url`** for transition logging via `logTransition('touch-phase', url, from, to)`. Not in the original spec but essential for quake console diagnostics.
- **Reducer uses `reduceTouchPhase(state, event)` not `dispatch(event)`** — the hook wraps it in `setTouchPhase(current => reduceTouchPhase(current, { type: eventType }))` using the functional updater form of useState. This ensures transitions always reference the latest state.
- **`pointerHandlers` spread on the card's inner `motion.div`** (the one with `drag`, `onClick`, etc.) rather than the outer Selectable wrapper. Both layers' pointer handlers fire independently.

### Verified edge cases

- **Scroll cancellation**: finger moves > 10px → `MOVE_EXCEEDED` → idle. Confirmed via `onPointerMove` threshold check.
- **Long press → selection**: 500ms AUTO_CANCEL fires → idle. Selectable's long-press timer fires simultaneously → enters selection mode. No RELEASED phase, no summary request. Correct.
- **Rapid re-tap**: pointerDown during RELEASED clears the release timer and re-enters PRESSED. Works naturally.
- **pointerCancel**: browser-initiated cancel (e.g., system gesture) → dispatches `POINTER_CANCEL` → idle. Logged in quake console.
