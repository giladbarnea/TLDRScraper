---
last_updated: 2026-01-06 16:47, cbfe651
---
# Plan C Implementation: Overscroll-Up Completion Gesture

## Deviations from Plan C and Review

### Used: Native Event Listeners (Not Framer Motion)

Plan C proposed using touch events, which was correct. The implementation follows the same pattern established in Plan B's `usePullToClose`—native `addEventListener` with `{ passive: false }` for `touchmove`. This allows `e.preventDefault()` to block native overscroll rubber-banding when the gesture activates.

### Fixed: Event Listener Thrashing

The Review correctly identified that the proposed hook had `isOverscrolling` and `overscrollAmount` in the `useEffect` dependency array. This would cause listener thrashing on every frame.

Solution: Use refs for internal gesture state (`startY`, `isOverscrolling`, `overscrollOffsetRef`) and only use `useState` to push updates to the UI. The `useEffect` dependencies are now stable: `[scrollRef, onComplete, threshold]`.

### Added: Content Resistance Transform

The Review noted the "kinetic disconnect" issue—content feeling stuck while dragging. The implementation applies a resistance transform to the content wrapper:

```jsx
transform: `translateY(-${overscrollOffset * 0.4}px)`
```

This makes the content move with the finger at 40% of the drag distance, providing visual feedback that matches the direct manipulation metaphor.

## Final Implementation

### `useOverscrollUp` Hook

`client/src/hooks/useOverscrollUp.js`

Parameters:
- `scrollRef`: Element to check scroll position and attach listeners
- `onComplete`: Callback when threshold exceeded
- `threshold`: Pixels required to trigger completion (default 60)

Returns `{ overscrollOffset, isOverscrolling, progress, isComplete }`.

### Bottom Detection

```js
const isAtBottom = () => {
  const { scrollTop, scrollHeight, clientHeight } = scrollEl
  return scrollHeight - scrollTop - clientHeight < 1
}
```

Gesture only activates when user is at the absolute bottom (within 1px tolerance for subpixel rendering).

### Drag Direction

Unlike `usePullToClose` which tracks downward movement (`diff > 0`), this hook tracks upward movement:

```js
const deltaY = startY.current - e.touches[0].clientY
if (deltaY > 0 && isAtBottom()) { ... }
```

Positive `deltaY` means finger moved up (start Y was higher than current Y in screen coordinates).

### Threshold Mechanics

The threshold works differently from Plan B:
- `overscrollOffset` is capped at `threshold * 1.5` (90px) for visual overshoot
- Completion triggers at `threshold * 0.5` (30px) of actual offset
- This accounts for the 0.5 resistance factor applied during drag

### Integration

In `ZenModeOverlay`:

```jsx
const { overscrollOffset, isOverscrolling, progress: overscrollProgress, isComplete: overscrollComplete } = useOverscrollUp({
  scrollRef,
  onComplete: onMarkDone,
  threshold: 60
})
```

Listeners attach to `scrollRef` (the scrollable content area), same element used for scroll position checking.

### Completion Zone UI

A hidden-by-default zone at the bottom of scroll content:
- Fades in when `isOverscrolling` is true
- Checkmark icon scales and increases opacity with `progress`
- Background turns green and scales up when `isComplete`

The zone has `py-16` padding, adding ~128px of whitespace at the bottom. This doubles as comfortable bottom padding for reading on mobile.

## Files Changed

- `client/src/hooks/useOverscrollUp.js` (new)
- `client/src/components/ArticleCard.jsx` (modified `ZenModeOverlay`)
