import { useAnimation, useDragControls } from 'framer-motion'
import { useEffect, useState } from 'react'

export function useSwipeDown({ onSwipeComplete }) {
  const [isDragging, setIsDragging] = useState(false)
  const controls = useAnimation()
  const dragControls = useDragControls()

  useEffect(() => {
    controls.start({
      y: 0,
      opacity: 1,
      scale: 1,
      transition: { type: 'spring', damping: 25, stiffness: 300 }
    })
  }, [controls])

  const startDrag = (event) => {
    dragControls.start(event)
  }

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
        transition: { duration: 0.2, ease: 'easeOut' }
      })
      onSwipeComplete()
    } else {
      controls.start({ y: 0, opacity: 1 })
    }
  }

  return {
    isDragging,
    controls,
    dragControls,
    startDrag,
    handleDragStart,
    handleDragEnd,
  }
}
