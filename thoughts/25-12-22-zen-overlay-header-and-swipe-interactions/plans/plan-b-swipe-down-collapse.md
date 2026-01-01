---
last_updated: 2026-01-01 06:21, 95a000c
---
# Plan B: Swipe-Down Collapse Gesture

## Overview

This plan suggests adding a swipe-down gesture to the Zen overlay that would collapse it (similar to the down chevron button). The idea is that pulling down on the header or top of content would dismiss the overlay while preserving article state.

## Current State Analysis

**Current Close Mechanisms** (`ArticleCard.jsx:30-40, 46-51`):

- Escape key press → `onClose()`
- Down chevron button click → `onClose()`
- No gesture support exists inside ZenModeOverlay

**Existing Gesture Pattern** (`useSwipeToRemove.js`):

- Uses Framer Motion’s `drag` prop with `useAnimation`
- Threshold-based: offset or velocity triggers action
- Animates element off-screen before callback

## Desired End State

**Swipe-Down Behavior**:

- User could drag down from header area or top of content
- Visual feedback would show the overlay translating down with drag
- A threshold (drag > 80px OR velocity > 500px/s) would trigger dismiss
- Releasing before threshold would snap back to position
- On dismiss: animate overlay down + fade out, then call `onClose()`

**Verification**:

1. Swipe down from header should slide overlay down and close it
1. Swipe down from content top should exhibit the same behavior
1. Light swipe (< threshold) should bounce overlay back
1. Fast flick (high velocity) should trigger dismiss even with small offset
1. After dismiss, article state should remain unchanged (not marked read/removed)

## What We’re NOT Doing

- Horizontal swipe gestures
- Overscroll-up gesture (Plan C)
- Modifying the existing swipe-to-remove on ArticleCard
- Adding gesture support to the scroll content area (only header/top)

## Implementation Approach

Consider creating a new hook `useSwipeDown` following the pattern of `useSwipeToRemove`, then integrating it into `ZenModeOverlay` using Framer Motion’s drag capabilities.

## Phase 1: Create Swipe-Down Hook

### Overview

You might want to create a reusable hook for vertical swipe-down detection with animation controls.

### Suggested Changes:

#### 1. Create useSwipeDown Hook

**File**: `client/src/hooks/useSwipeDown.js` (new file)
**Changes**: Consider adding a new hook for vertical swipe detection

```jsx
import { useAnimation } from 'framer-motion'
import { useState } from 'react'

export function useSwipeDown({ onSwipeComplete }) {
  const [isDragging, setIsDragging] = useState(false)
  const controls = useAnimation()

  const handleDragStart = () => {
    setIsDragging(true)
  }

  const handleDragEnd = async (_event, info) => {
    setIsDragging(false)
    const { offset, velocity } = info
    const swipeThreshold = 80
    const velocityThreshold = 500

    if (offset.y > swipeThreshold || velocity.y > velocityThreshold) {
      await controls.start({
        y: window.innerHeight,
        opacity: 0,
        transition: { duration: 0.2, ease: "easeOut" }
      })
      onSwipeComplete()
    } else {
      controls.start({ y: 0, opacity: 1 })
    }
  }

  return {
    isDragging,
    controls,
    handleDragStart,
    handleDragEnd,
  }
}
```

-----

## Phase 2: Integrate into ZenModeOverlay

### Overview

This phase suggests applying drag behavior to the overlay container, constrained to downward movement only.

### Suggested Changes:

#### 1. Import Dependencies

**File**: `client/src/components/ArticleCard.jsx`
**Changes**: You’ll want to add imports for motion and the new hook

```jsx
// Line 1: Ensure motion is imported (already is)
import { motion } from 'framer-motion'

// Consider adding this new import after line 8
import { useSwipeDown } from '../hooks/useSwipeDown'
```

#### 2. Use Hook in ZenModeOverlay

**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Consider adding hook usage inside ZenModeOverlay function

```jsx
// Inside ZenModeOverlay, after the useState for hasScrolled (from Plan A)
const { isDragging, controls, handleDragStart, handleDragEnd } = useSwipeDown({
  onSwipeComplete: onClose
})
```

#### 3. Convert Inner Container to motion.div

**File**: `client/src/components/ArticleCard.jsx`
**Changes**: You might replace the inner div with a draggable motion.div

Current (after Plan A):

```jsx
<div className="w-full h-full bg-white flex flex-col animate-zen-enter">
```

Suggested:

```jsx
<motion.div
  drag="y"
  dragConstraints={{ top: 0, bottom: 0 }}
  dragElastic={{ top: 0, bottom: 0.6 }}
  dragMomentum={false}
  animate={controls}
  initial={{ y: 0, opacity: 1 }}
  onDragStart={handleDragStart}
  onDragEnd={handleDragEnd}
  className="w-full h-full bg-white flex flex-col animate-zen-enter"
  style={{ touchAction: 'pan-x' }}
>
```

**Key configurations**:

- `drag="y"` - Restricts to vertical drag only
- `dragConstraints={{ top: 0, bottom: 0 }}` - Prevents dragging up, snaps back from down
- `dragElastic={{ top: 0, bottom: 0.6 }}` - No elasticity up, moderate down
- `dragMomentum={false}` - Prevents continued motion after release
- `style={{ touchAction: 'pan-x' }}` - Allows horizontal scroll (for text selection) while capturing vertical

#### 4. Update Closing Tag

**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Remember to update the closing tag to match

```jsx
</motion.div>  // was </div>
```

### Success Criteria:

#### Automated Verification:

- [ ] Client should build without errors: `cd client && npm run build`
- [ ] Linter should pass: `cd client && npm run lint`
- [ ] New hook file should exist: `client/src/hooks/useSwipeDown.js`

#### Manual Verification:

- [ ] Opening a TLDR overlay should work as before
- [ ] Touching/clicking header and dragging down should move overlay with finger/cursor
- [ ] Dragging down > 80px and releasing should animate overlay away and close it
- [ ] Dragging down < 80px and releasing should snap overlay back to position
- [ ] Quick flick down (fast velocity) should trigger dismiss even with small distance
- [ ] Dragging up should show no movement (constrained)
- [ ] After swipe-dismiss, article state should remain unchanged (not read, not removed)
- [ ] Escape key and chevron button should still work

**Implementation Note**: After completing this phase and confirming all automated verification passes, you might want to pause here for manual confirmation that the manual testing was successful before proceeding to Plan C.

-----

## Technical Notes

### Why a Separate Hook?

Following the existing pattern of `useSwipeToRemove`, it would be beneficial to encapsulate gesture logic in a hook for:

1. Testability
1. Reusability (could be used elsewhere if needed)
1. Separation of concerns

### Interaction with Scroll

The `touchAction: 'pan-x'` style would allow:

- Vertical swipe on the overlay container (for dismiss gesture)
- Horizontal pan for text selection within content

The content scroll area (`overflow-y-auto`) would be a child element, so its native scrolling should work independently. The drag gesture would only activate when touching the overlay container directly (header area), not when scrolling content.

### Threshold Rationale

- **Offset threshold (80px)**: Slightly less than `useSwipeToRemove` (100px) because vertical swipes tend to feel more intentional
- **Velocity threshold (500px/s)**: Higher than horizontal (300px/s) to help prevent accidental dismisses during scroll attempts

-----

## References

- Original discussion: `thoughts/25-12-22-zen-overlay-header-and-swipe-interactions/discussion.md`
- Existing swipe pattern: `client/src/hooks/useSwipeToRemove.js`
- Framer Motion drag docs: https://www.framer.com/motion/gestures/#drag