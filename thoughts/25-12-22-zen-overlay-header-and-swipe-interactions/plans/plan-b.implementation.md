---
last_updated: 2026-01-05 08:37
---
# Plan B Implementation: Pull-to-Close Gesture

## Deviations from Plan B and Review

### Not Used: Framer Motion Drag

Plan B proposed using Framer Motion's `drag="y"` with `useAnimation`. The Review suggested `useDragControls` to restrict drag initiation to the header.

Neither approach was used. Framer Motion's drag system conflicts with scrollable content because it captures touch events at the container level, interfering with native scroll behavior inside child elements.

### Not Used: `touchAction` CSS

Plan B suggested `touchAction: 'pan-x'` to allow horizontal pan while capturing vertical gestures. This doesn't solve the scroll conflict—it just changes which axis the browser handles natively.

## What Didn't Work

### First Attempt: React Touch Event Props

Initial implementation used React's `onTouchStart`, `onTouchMove`, `onTouchEnd` props with `e.preventDefault()` to block native scroll during the pull gesture.

Result: Only the content appeared to move, not the header.

Cause: React 17+ attaches touch listeners as passive by default. Passive listeners ignore `preventDefault()`, so native iOS overscroll rubber-banding still triggered on the scrollable content area—creating the illusion that only content moved.

### Transform Location

Tried applying `transform: translateY()` to the inner container vs. the outer `fixed` container. Made no difference, confirming the issue wasn't about transform placement but about native overscroll not being suppressed.

## Final Implementation

### `usePullToClose` Hook

`client/src/hooks/usePullToClose.js`

Uses native `addEventListener` with `{ passive: false }` for `touchmove`. This allows `e.preventDefault()` to actually block native scroll/overscroll behavior.

Parameters:
- `containerRef`: Element where touch listeners attach (the overlay wrapper containing both header and content)
- `scrollRef`: Element used to check `scrollTop` (the scrollable content area)
- `onClose`: Callback when threshold exceeded
- `threshold`: Pixels required to trigger close (default 80)

Returns `{ pullOffset }` for applying the transform.

### Scroll-Aware Activation

```js
const handleTouchStart = (e) => {
  const touchedScrollArea = scrollRef.current?.contains(e.target)
  if (!touchedScrollArea || scrollRef.current?.scrollTop === 0) {
    startY.current = e.touches[0].clientY
  }
}
```

- Touch on header: Always activates (header doesn't scroll, so no conflict)
- Touch on content: Only activates when `scrollTop === 0`

This avoids the "pull-to-refresh style logic" the Review called complex. It's one conditional.

### Why Two Refs

The Review suggested restricting drag to the header via `useDragControls`. Instead, we allow drag from anywhere but gate the content-area drag on scroll position. This required separating:

1. Where listeners attach (`containerRef` = header + content)
2. Where scroll position is checked (`scrollRef` = content only)

### Integration

In `ZenModeOverlay`:

```jsx
const containerRef = useRef(null)
const scrollRef = useRef(null)
const { pullOffset } = usePullToClose({ containerRef, scrollRef, onClose })
```

Transform applied to the outermost `fixed` container so the entire overlay (header + content) moves as one unit.

## Files Changed

- `client/src/hooks/usePullToClose.js` (new)
- `client/src/components/ArticleCard.jsx` (modified `ZenModeOverlay`)
