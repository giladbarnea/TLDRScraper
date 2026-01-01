---
description: Review of Plan B (Swipe-Down Collapse)
last_updated: 2026-01-01 05:58, 24ce6b6
---
# Plan Review: Swipe-Down Collapse Gesture

## Summary of the Plan
The plan proposes adding a "swipe-down to dismiss" gesture to the `ZenModeOverlay` component. It involves:
1.  Creating a `useSwipeDown` hook (similar to the existing `useSwipeToRemove` pattern).
2.  Wrapping the content of `ZenModeOverlay` (which is a Portal) in a Framer Motion `motion.div`.
3.  Configuring `drag="y"` on this wrapper to allow the user to drag the entire overlay down to close it.

## Codebase Context
- **`ZenModeOverlay`**: A functional component inside `ArticleCard.jsx`, rendered via `createPortal`.
- **Structure**: It contains a header (`flex items-center...`) and a scrollable content area (`overflow-y-auto`).
- **Existing Patterns**: `useSwipeToRemove` uses `useAnimation` and drag constraints.
- **Conflict Risk**: The overlay contains a vertically scrollable child (`div className="overflow-y-auto..."`).

## Assessment

### 1. Major Design Flaw: Drag vs. Scroll Conflict
The plan proposes applying `drag="y"` and `style={{ touchAction: 'pan-x' }}` to the **parent container** of the scrollable text.
- **The Issue**: Framer Motion's `drag="y"` captures vertical touch gestures. Even if the child has `overflow-y-auto`, the parent's drag listener often takes precedence or conflicts with native scrolling, especially on mobile devices.
- **The Plan's Assertion**: *"The content scroll area is a child element, so its native scrolling works independently."* -> **This is likely incorrect.** When `touch-action: pan-x` (or `none`) is applied to a container to enable Framer Motion dragging, it explicitly disables the browser's native vertical scrolling handling for that area to allow the script to handle it. This will likely make the article content **unscrollable**.

### 2. Conflicting Animations
- **The Issue**: The plan keeps the Tailwind class `animate-zen-enter` on the same element it turns into a `motion.div` with `initial` and `animate` props.
- **Impact**: CSS animations and JS-driven Framer Motion animations fighting for control over opacity/transform can lead to glitches or one being ignored.
- **Solution**: Since we are introducing Framer Motion, we should fully migrate the entrance animation to the `initial`/`animate` props and remove the `animate-zen-enter` class.

## Recommendations

### Approve with Modifications

The plan requires two critical changes to work reliably:

**1. Restrict Drag Handle (or handle scroll conflict)**
Instead of making the whole card the drag target, use **Drag Controls** to limit the drag initiation to the **Header** only. This guarantees the scrollable content remains scrollable.

*Alternative*: If the requirement "swipe down from top of content" is strict, you would need to implement a "pull-to-refresh" style logic where drag is only enabled when `scrollTop === 0`. This is significantly more complex. **Recommendation:** Start by restricting drag to the header using `dragControls`.

**2. Remove CSS Animation Class**
Remove `animate-zen-enter` and define the entrance animation in Framer Motion props.

### Modified Implementation Steps

#### A. Use Drag Controls
```jsx
// In ZenModeOverlay
const dragControls = useDragControls()

function startDrag(event) {
  dragControls.start(event)
}

return (
  <motion.div
    drag="y"
    dragListener={false} // <--- Key change: Disable default listener
    dragControls={dragControls} // <--- Pass controls
    // ... other props
  >
    <div 
      onPointerDown={startDrag} // <--- Attach listener to Header only
      className="flex items-center gap-3 p-5..."
    >
      {/* Header content */}
    </div>
    
    {/* Scrollable content remains untouched */}
  </motion.div>
)
```

#### B. Migrate Animation
```jsx
<motion.div
  // ...
  className="w-full h-full bg-white flex flex-col" // Remove animate-zen-enter
  initial={{ y: "100%", opacity: 0 }} // Define slide-up entrance here
  animate={{ y: 0, opacity: 1 }}
  exit={{ y: "100%", opacity: 0 }}
  transition={{ type: "spring", damping: 25, stiffness: 300 }}
>
```

## Final Verdict
The core logic of `useSwipeDown` is sound, but the **integration into `ZenModeOverlay` needs to be more surgical** to avoid breaking the core reading experience (scrolling). **Adopt the Drag Controls pattern.**
