import { useAnimation } from 'framer-motion'
import { useEffect, useState } from 'react'

export function useSwipeToRemove({ isRemoved, stateLoading, onSwipeComplete }) {
  const [isDragging, setIsDragging] = useState(false)
  const [dragError, setDragError] = useState(null)
  const controls = useAnimation()

  const canDrag = !isRemoved && !stateLoading

  useEffect(() => {
    controls.start({
      opacity: isDragging ? 1 : stateLoading ? 0.4 : isRemoved ? 0.5 : 1,
      filter: stateLoading || isRemoved ? 'grayscale(100%)' : 'grayscale(0%)',
      x: 0,
    })
  }, [isDragging, isRemoved, stateLoading, controls])

  const handleDragStart = () => {
    setIsDragging(true)
    setDragError(null)
  }

  const handleDragEnd = async (_event, info) => {
    setIsDragging(false)
    try {
      const { offset, velocity } = info
      const swipeThreshold = -100
      const velocityThreshold = -300

      if (offset.x < swipeThreshold || velocity.x < velocityThreshold) {
        await controls.start({
          x: -window.innerWidth,
          opacity: 0,
          transition: { duration: 0.2, ease: "easeOut" }
        })
        onSwipeComplete()
      } else {
        controls.start({ x: 0 })
      }
    } catch (error) {
      setDragError(`Drag error: ${error.message}`)
      controls.start({ x: 0 })
    }
  }

  const clearDragError = () => setDragError(null)

  return {
    isDragging,
    dragError,
    clearDragError,
    controls,
    canDrag,
    handleDragStart,
    handleDragEnd,
  }
}
