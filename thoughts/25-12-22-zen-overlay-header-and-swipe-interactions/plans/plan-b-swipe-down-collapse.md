---
last_updated: 2025-12-31 10:13, da59643
---
# Plan B: Swipe-Down Collapse Gesture

## Overview

Add a swipe-down gesture to the Zen overlay that collapses it (same as the down chevron button). Pulling down on the header or top of content dismisses the overlay while preserving article state.

## Current State Analysis

**Current Close Mechanisms** (`ArticleCard.jsx:30-40, 46-51`):
- Escape key press → `onClose()`
- Down chevron button click → `onClose()`
- No gesture support exists inside ZenModeOverlay

**Existing Gesture Pattern** (`useSwipeToRemove.js`):
- Uses Framer Motion's `drag` prop with `useAnimation`
- Threshold-based: offset or velocity triggers action
- Animates element off-screen before callback

## Desired End State

**Swipe-Down Behavior**:
- User drags down from header area or top of content
- Visual feedback: overlay translates down with drag
- Threshold: drag > 80px OR velocity > 500px/s triggers dismiss
- Release before threshold: snaps back to position
- On dismiss: animate overlay down + fade out, then call `onClose()`

**Verification**:
1. Swipe down from header → overlay slides down and closes
2. Swipe down from content top → same behavior
3. Light swipe (< threshold) → overlay bounces back
4. Fast flick (high velocity) → triggers dismiss even with small offset
5. After dismiss, article state unchanged (not marked read/removed)

## What We're NOT Doing

- Horizontal swipe gestures
- Overscroll-up gesture (Plan C)
- Modifying the existing swipe-to-remove on ArticleCard
- Adding gesture support to the scroll content area (only header/top)

## Implementation Approach

Create a new hook `useSwipeDown` following the pattern of `useSwipeToRemove`, then integrate it into `ZenModeOverlay` using Framer Motion's drag capabilities.

## Phase 1: Create Swipe-Down Hook

### Overview
Create a reusable hook for vertical swipe-down detection with animation controls.

### Changes Required:

#### 1. Create useSwipeDown Hook
**File**: `client/src/hooks/useSwipeDown.js` (new file)
**Changes**: New hook for vertical swipe detection

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

---

## Phase 2: Integrate into ZenModeOverlay

### Overview
Apply drag behavior to the overlay container, constrained to downward movement only.

### Changes Required:

#### 1. Import Dependencies
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Add imports for motion and the new hook

```jsx
// Line 1: Ensure motion is imported (already is)
import { motion } from 'framer-motion'

// Add new import after line 8
import { useSwipeDown } from '../hooks/useSwipeDown'
```

#### 2. Use Hook in ZenModeOverlay
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Add hook usage inside ZenModeOverlay function

```jsx
// Inside ZenModeOverlay, after the useState for hasScrolled (from Plan A)
const { isDragging, controls, handleDragStart, handleDragEnd } = useSwipeDown({
  onSwipeComplete: onClose
})
```

#### 3. Convert Inner Container to motion.div
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Replace the inner div with a draggable motion.div

Current (after Plan A):
```jsx
<div className="w-full h-full bg-white flex flex-col animate-zen-enter">
```

New:
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
- `drag="y"` - Only vertical drag
- `dragConstraints={{ top: 0, bottom: 0 }}` - Can't drag up, snaps back from down
- `dragElastic={{ top: 0, bottom: 0.6 }}` - No elasticity up, moderate down
- `dragMomentum={false}` - No continued motion after release
- `style={{ touchAction: 'pan-x' }}` - Allow horizontal scroll (for text selection) but capture vertical

#### 4. Update Closing Tag
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Update the closing tag to match

```jsx
</motion.div>  // was </div>
```

### Success Criteria:

#### Automated Verification:
- [ ] Client builds without errors: `cd client && npm run build`
- [ ] Linter passes: `cd client && npm run lint`
- [ ] New hook file exists: `client/src/hooks/useSwipeDown.js`

#### Manual Verification:
- [ ] Open a TLDR overlay
- [ ] Touch/click header and drag down → overlay moves with finger/cursor
- [ ] Drag down > 80px and release → overlay animates away, closes
- [ ] Drag down < 80px and release → overlay snaps back to position
- [ ] Quick flick down (fast velocity) → triggers dismiss even with small distance
- [ ] Drag up → no movement (constrained)
- [ ] After swipe-dismiss, article state unchanged (not read, not removed)
- [ ] Escape key and chevron button still work

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to Plan C.

---

## Technical Notes

### Why a Separate Hook?

Following the existing pattern of `useSwipeToRemove`, gesture logic is encapsulated in a hook for:
1. Testability
2. Reusability (could be used elsewhere)
3. Separation of concerns

### Interaction with Scroll

The `touchAction: 'pan-x'` style allows:
- Vertical swipe on the overlay container (for dismiss gesture)
- Horizontal pan for text selection within content

The content scroll area (`overflow-y-auto`) is a child element, so its native scrolling works independently. The drag gesture only activates when touching the overlay container directly (header area), not when scrolling content.

### Threshold Rationale

- **Offset threshold (80px)**: Slightly less than `useSwipeToRemove` (100px) because vertical swipes feel more intentional
- **Velocity threshold (500px/s)**: Higher than horizontal (300px/s) to prevent accidental dismisses during scroll attempts

---

## References

- Original discussion: `thoughts/25-12-22-zen-overlay-header-and-swipe-interactions/discussion.md`
- Existing swipe pattern: `client/src/hooks/useSwipeToRemove.js`
- Framer Motion drag docs: https://www.framer.com/motion/gestures/#drag
- Plan A (prerequisite): `thoughts/25-12-22-zen-overlay-header-and-swipe-interactions/plans/plan-a-header-redesign.md`
