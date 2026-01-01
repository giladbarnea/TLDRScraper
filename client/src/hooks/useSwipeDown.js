import { useAnimation } from 'framer-motion'
import { useEffect, useRef } from 'react'

export function useSwipeDown({ onSwipeComplete, scrollRef }) {
  const controls = useAnimation()
  const gestureRef = useRef({ startY: 0, startScrollTop: 0, isDragging: false })

  useEffect(() => {
    controls.start({
      y: 0,
      opacity: 1,
      transition: { type: 'spring', damping: 25, stiffness: 300 }
    })
  }, [controls])

  const handlePointerDown = (e) => {
    const scrollTop = scrollRef.current?.scrollTop ?? 0
    gestureRef.current = { startY: e.clientY, startScrollTop: scrollTop, isDragging: false }
  }

  const handlePointerMove = (e) => {
    const { startY, startScrollTop, isDragging } = gestureRef.current
    const deltaY = e.clientY - startY

    if (startScrollTop === 0 && deltaY > 0) {
      if (!isDragging && deltaY > 12) {
        gestureRef.current.isDragging = true
        e.target.setPointerCapture(e.pointerId)
      }

      if (gestureRef.current.isDragging) {
        controls.set({ y: deltaY * 0.5, opacity: 1 })
      }
    }
  }

  const handlePointerUp = async (e) => {
    const { startY, isDragging } = gestureRef.current

    if (isDragging) {
      try {
        e.target.releasePointerCapture(e.pointerId)
      } catch {}

      const deltaY = e.clientY - startY
      const swipeThreshold = 80

      if (deltaY > swipeThreshold) {
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

    gestureRef.current = { startY: 0, startScrollTop: 0, isDragging: false }
  }

  return {
    controls,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
  }
}
