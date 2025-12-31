---
last_updated: 2025-12-31 07:37
---
# Plan Review: Overscroll-Up Completion Gesture

## Summary
The plan proposes adding a "pull-up to complete" gesture at the bottom of the Zen Mode article view. It involves a new `useOverscrollUp` hook that detects touch interactions when the user is at the bottom of the scroll container, and visual feedback in the form of a checkmark icon that fills up as the user pulls.

## Critical Analysis

### 1. Performance Hazard: Event Listener Thrashing
**Issue:** The `useEffect` in `useOverscrollUp` includes `isOverscrolling` and `overscrollAmount` in its dependency array.
```javascript
useEffect(() => {
  // ...
  const handleTouchMove = (e) => {
    // ...
    setOverscrollAmount(...) // Updates state
  }
  // ...
}, [..., isOverscrolling, overscrollAmount])
```
**Impact:** Every time `setOverscrollAmount` is called (which happens on every frame of the drag), the state updates, causing the `useEffect` to clean up (remove listeners) and re-run (add listeners). This constant thrashing of event listeners during a high-frequency gesture (60/120Hz) is poor for performance and can lead to stuttering.

**Solution:**
Use `useRef` to track the *internal* gesture logic (`touchStartY`, `currentOverscroll`, `isDraggingRef`) inside the event handlers. This allows the handlers to remain stable (no dependencies on changing state). Only use `setState` to push updates to the UI.

### 2. UX "Stuck" Feeling (Kinetic Disconnect)
**Issue:** The hook calls `e.preventDefault()` on `touchmove` to prevent native scrolling/rubber-banding. However, the plan implies only the *completion zone* (checkmark) animates.
**Impact:** The main article content will feel "locked" or "stuck" in place while the user drags their finger up. This breaks the direct manipulation metaphor—the user expects the "paper" to move with their finger, even if with resistance.

**Solution:**
Expose the `overscrollAmount` to the content container (not just the checkmark div) and apply a resistance transform.
```jsx
// In ArticleCard/ZenModeOverlay
<div style={{ transform: `translateY(-${overscrollAmount * 0.4}px)` }}>
  {/* Content */}
</div>
```

### 3. Missing Dependency: `onMarkDone`
**Issue:** The plan attempts to pass `onMarkDone` to `ZenModeOverlay` props:
`const { isOverscrolling... } = useOverscrollUp({ ..., onComplete: onMarkDone ... })`
However, the current `ZenModeOverlay` implementation in `ArticleCard.jsx` does not accept an `onMarkDone` prop (only `onClose`). This appears to rely on Plan A (Header Redesign) which is not yet applied.

**Solution:**
Ensure `onMarkDone` is added to `ZenModeOverlay` props if Plan A hasn't been merged, or explicitly note this dependency.

### 4. Layout Shift / Dead Space
**Issue:** The "completion zone" is implemented as a standard block `div` with `py-16` inside the scroll container.
**Impact:** This adds permanent ~128px (approx) whitespace to the bottom of every article, even when not overscrolling.
**Mitigation:** This is actually acceptable (and often desirable) as "bottom padding" for mobile reading, but it should be intentional.

### 5. Note: Consistency vs Complexity
**Observation:** The `ArticleCard` swipe-to-remove gesture uses Framer Motion (spring physics, elasticity). The proposed implementation uses raw touch events which will likely feel linear/stiff.
**Improvement Opportunity:** To match the app's tactile feel, we could use the raw touch events to drive a Framer Motion `useMotionValue` instead of React state. This would allow us to apply `dragElastic`-like math (logarithmic decay) and spring animations on release, ensuring the vertical overscroll feels physically consistent with the horizontal swipe.
**Trade-off:** This increases complexity (Hybrid approach: Raw Listeners + Motion Values) but yields higher polish.

## Refined Hook Implementation (Recommendation)

Here is a safer, more performant version of the hook pattern:

```javascript
export function useOverscrollUp({ scrollRef, onComplete, threshold = 60 }) {
  const [state, setState] = useState({ isOverscrolling: false, overscrollAmount: 0 })
  
  // Refs for mutable logic to avoid effect re-runs
  const gestureState = useRef({
    startY: null,
    isAtBottom: false,
    isDragging: false,
    currentAmount: 0
  })

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return

    const handleTouchStart = (e) => {
      // Check bottom logic...
      // Update gestureState.current
    }

    const handleTouchMove = (e) => {
      if (!gestureState.current.isDragging) return
      
      // Calculate delta
      // e.preventDefault()
      
      // Update Ref AND State (for UI)
      gestureState.current.currentAmount = delta
      setState({ isOverscrolling: true, overscrollAmount: delta })
    }

    // ... handleTouchEnd ...

    // Dependencies are now stable!
    el.addEventListener('touchstart', handleTouchStart, { passive: true })
    el.addEventListener('touchmove', handleTouchMove, { passive: false })
    // ...
  }, [scrollRef, threshold, onComplete]) // No state dependencies

  return { ...state, progress: Math.min(state.overscrollAmount / threshold, 1) }
}
```

## Verdict
**Approve with Modifications**.
The core idea is solid, but the implementation needs to fix the `useEffect` performance hazard and should address the static content feel.

1.  **Refactor `useOverscrollUp`** to avoid listener thrashing (use refs).
2.  **Add `translateY`** to the main content wrapper so it moves with the gesture.
3.  **Verify `onMarkDone`** availability.
