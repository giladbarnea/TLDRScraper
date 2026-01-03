---
last_updated: 2026-01-03 14:52
---
# Plan B Revised: Pull-to-Refresh Style Dismiss

## Core Insight

Use **conditional drag initiation** — only start drag when `scrollTop === 0` at pointer down.

## Implementation

```jsx
const scrollRef = useRef(null)
const dragControls = useDragControls()

const handlePointerDown = (e) => {
  if (scrollRef.current?.scrollTop <= 0) {
    dragControls.start(e)
  }
}

const handleDragEnd = async (_event, info) => {
  const { offset, velocity } = info
  if (offset.y > 80 || velocity.y > 500) {
    await controls.start({ y: '100%', opacity: 0, transition: { duration: 0.2 } })
    onClose()
  } else {
    controls.start({ y: 0, opacity: 1 })
  }
}

return (
  <motion.div
    drag="y"
    dragControls={dragControls}
    dragListener={false}
    dragConstraints={{ top: 0, bottom: 0 }}
    dragElastic={{ top: 0, bottom: 0.5 }}
    animate={controls}
    onDragEnd={handleDragEnd}
    onPointerDown={handlePointerDown}
  >
    <div>{/* Header */}</div>
    <div ref={scrollRef} className="overflow-y-auto">
      {/* Content */}
    </div>
  </motion.div>
)
```

## Why This Works

- `dragListener={false}` prevents auto-capture of vertical gestures
- `dragControls.start(e)` only called when at scroll top
- Native scroll works normally when scrolled down
- Once drag starts, Framer Motion owns the gesture until release

## UX Flow

1. **Scrolled down** → pointer down does nothing → native scroll
2. **At top + pull down** → drag gesture starts → overlay slides down
3. **Release past threshold** → dismiss
4. **Release before threshold** → snap back
