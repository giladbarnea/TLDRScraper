---
last_updated: 2025-12-31 07:37
---
# Plan C: Overscroll-Up Completion Gesture

## Overview

Add an overscroll-up gesture at the bottom of the Zen overlay content. When the user reaches the end and continues dragging up, a checkmark icon appears and releasing triggers the "mark done" action (same as the checkmark button).

## Current State Analysis

**Current Scroll Behavior** (`ArticleCard.jsx:65-72`):
- Content area uses native `overflow-y-auto` scrolling
- `useScrollProgress` tracks scroll position (0-1)
- No overscroll behavior or detection exists

**Desired "Mark Done" Action** (from Plan A):
- Calls `tldr.collapse()` then `toggleRemove()`
- Article removed from list, overlay closes

## Desired End State

**Overscroll-Up Behavior**:
1. User scrolls to bottom of content (progress = 1)
2. User continues dragging up (overscroll)
3. Visual feedback: checkmark icon fades in at bottom of viewport
4. Threshold: overscroll > 60px fills/activates the checkmark
5. Release at threshold: triggers "mark done"
6. Release before threshold: content bounces back, no action

**Verification**:
1. Scroll to bottom → can overscroll up
2. Overscroll reveals checkmark icon that fills/animates
3. Release past threshold → article marked removed, overlay closes
4. Release before threshold → bounces back, nothing happens
5. Overscroll only works at bottom (not during normal scroll)

## What We're NOT Doing

- Changing the swipe-down gesture (Plan B)
- Overscroll-down at top
- Modifying native scroll physics
- Adding haptic feedback (browser limitation)

## Implementation Approach

Use a combination of:
1. Track when at scroll bottom via `useScrollProgress`
2. Add a "footer zone" that appears on overscroll
3. Use touch events to detect overscroll when at bottom
4. Framer Motion for the checkmark reveal animation

This is more complex than swipe-down because we need to detect overscroll on an already-scrolled container.

## Phase 1: Add Overscroll Detection

### Overview
Track overscroll distance when user drags up while at scroll bottom.

### Changes Required:

#### 1. Create useOverscrollUp Hook
**File**: `client/src/hooks/useOverscrollUp.js` (new file)
**Changes**: New hook for bottom overscroll detection

```jsx
import { useCallback, useEffect, useRef, useState } from 'react'

export function useOverscrollUp({ scrollRef, onComplete, threshold = 60 }) {
  const [overscrollAmount, setOverscrollAmount] = useState(0)
  const [isOverscrolling, setIsOverscrolling] = useState(false)
  const touchStartY = useRef(null)
  const isAtBottom = useRef(false)

  const checkIfAtBottom = useCallback(() => {
    const el = scrollRef.current
    if (!el) return false
    const { scrollTop, scrollHeight, clientHeight } = el
    return scrollHeight - scrollTop - clientHeight < 1
  }, [scrollRef])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return

    const handleTouchStart = (e) => {
      if (checkIfAtBottom()) {
        isAtBottom.current = true
        touchStartY.current = e.touches[0].clientY
      }
    }

    const handleTouchMove = (e) => {
      if (!isAtBottom.current || touchStartY.current === null) return

      const currentY = e.touches[0].clientY
      const deltaY = touchStartY.current - currentY

      if (deltaY > 0 && checkIfAtBottom()) {
        setIsOverscrolling(true)
        setOverscrollAmount(Math.min(deltaY, threshold * 1.5))
        e.preventDefault()
      } else {
        setIsOverscrolling(false)
        setOverscrollAmount(0)
      }
    }

    const handleTouchEnd = () => {
      if (isOverscrolling && overscrollAmount >= threshold) {
        onComplete()
      }
      setIsOverscrolling(false)
      setOverscrollAmount(0)
      touchStartY.current = null
      isAtBottom.current = false
    }

    el.addEventListener('touchstart', handleTouchStart, { passive: true })
    el.addEventListener('touchmove', handleTouchMove, { passive: false })
    el.addEventListener('touchend', handleTouchEnd, { passive: true })

    return () => {
      el.removeEventListener('touchstart', handleTouchStart)
      el.removeEventListener('touchmove', handleTouchMove)
      el.removeEventListener('touchend', handleTouchEnd)
    }
  }, [scrollRef, checkIfAtBottom, threshold, onComplete, isOverscrolling, overscrollAmount])

  const progress = Math.min(overscrollAmount / threshold, 1)

  return {
    isOverscrolling,
    overscrollAmount,
    progress,
    isComplete: progress >= 1
  }
}
```

---

## Phase 2: Add Completion Zone UI

### Overview
Render a checkmark icon that appears and fills as user overscrolls.

### Changes Required:

#### 1. Import Hook and Icon
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Add imports

```jsx
// Add to lucide-react import (already has Check from Plan A)
import { ..., CheckCircle2 } from 'lucide-react'

// Add new import after other hooks
import { useOverscrollUp } from '../hooks/useOverscrollUp'
```

#### 2. Use Hook in ZenModeOverlay
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Add hook usage inside ZenModeOverlay

```jsx
// Inside ZenModeOverlay, after the useSwipeDown hook (from Plan B)
const { isOverscrolling, progress: overscrollProgress, isComplete: overscrollComplete } = useOverscrollUp({
  scrollRef,
  onComplete: onMarkDone,
  threshold: 60
})
```

#### 3. Add Completion Zone to Content Area
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Add visual feedback zone after the prose content

Current content area (approximate, after Plan A):
```jsx
<div ref={scrollRef} className="overflow-y-auto flex-1 p-6 md:p-8 bg-white">
  <div className="max-w-3xl mx-auto">
    <div
      className="prose prose-slate ..."
      dangerouslySetInnerHTML={{ __html: html }}
    />
  </div>
</div>
```

New content area with completion zone:
```jsx
<div ref={scrollRef} className="overflow-y-auto flex-1 bg-white">
  <div className="p-6 md:p-8">
    <div className="max-w-3xl mx-auto">
      <div
        className="prose prose-slate max-w-none font-serif text-slate-700 leading-relaxed text-lg prose-p:my-3 prose-headings:text-slate-900"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  </div>

  {/* Overscroll completion zone */}
  <div
    className={`
      flex items-center justify-center py-16 transition-all duration-150
      ${isOverscrolling ? 'opacity-100' : 'opacity-0'}
    `}
    style={{
      transform: `translateY(${isOverscrolling ? 0 : 20}px)`,
    }}
  >
    <div
      className={`
        w-12 h-12 rounded-full flex items-center justify-center transition-all duration-150
        ${overscrollComplete
          ? 'bg-green-500 text-white scale-110'
          : 'bg-slate-100 text-slate-400'}
      `}
    >
      <CheckCircle2
        size={24}
        style={{
          opacity: 0.3 + overscrollProgress * 0.7,
          transform: `scale(${0.8 + overscrollProgress * 0.2})`
        }}
      />
    </div>
  </div>
</div>
```

### Success Criteria:

#### Automated Verification:
- [ ] Client builds without errors: `cd client && npm run build`
- [ ] Linter passes: `cd client && npm run lint`
- [ ] New hook file exists: `client/src/hooks/useOverscrollUp.js`

#### Manual Verification (requires touch device or touch emulation):
- [ ] Open a TLDR overlay with enough content to scroll
- [ ] Scroll to the absolute bottom of content
- [ ] Continue dragging up (overscroll) → checkmark icon appears
- [ ] Drag more → checkmark fills in / grows / turns green
- [ ] Release when checkmark is green → article marked removed, overlay closes
- [ ] Release before checkmark is green → bounces back, nothing happens
- [ ] Overscroll in the middle of content (not at bottom) → no effect
- [ ] Desktop mouse scroll → normal scroll, no overscroll zone appears

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful.

---

## Technical Notes

### Why Touch Events Instead of Framer Motion Drag?

The content area already has native `overflow-y-auto` scrolling. Adding Framer Motion drag would conflict with this. Instead:
1. Native scroll handles normal scrolling
2. Touch events intercept when at bottom and user continues upward
3. `e.preventDefault()` in touchmove stops further scroll while overscrolling

### Desktop Behavior

This implementation is touch-first. Desktop users:
- Can use the checkmark button (from Plan A)
- Mouse wheel overscroll doesn't trigger completion zone
- This matches iOS/Android patterns where overscroll gestures are touch-based

### Threshold Rationale

- **60px threshold**: Enough to feel intentional, not so much that it's tiring
- **1.5x visual max**: Allows visual progress beyond 100% for "pull harder" feedback before release

### Edge Cases

1. **Short content (no scroll needed)**: User is already at bottom from start, overscroll works immediately
2. **Rapid scroll to bottom**: Small delay before overscroll activates (touchstart happens first)
3. **Horizontal scroll during overscroll**: Not affected (we only track vertical)

---

## References

- Original discussion: `thoughts/25-12-22-zen-overlay-header-and-swipe-interactions/discussion.md`
- Plan A (prerequisite): `thoughts/25-12-22-zen-overlay-header-and-swipe-interactions/plans/plan-a-header-redesign.md`
- Plan B (context): `thoughts/25-12-22-zen-overlay-header-and-swipe-interactions/plans/plan-b-swipe-down-collapse.md`
- Scroll progress hook: `client/src/hooks/useScrollProgress.js`
