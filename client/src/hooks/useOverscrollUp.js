import { useEffect, useRef, useState } from 'react'

export function useOverscrollUp({ scrollRef, onComplete, threshold = 60 }) {
  const [overscrollOffset, setOverscrollOffset] = useState(0)
  const overscrollOffsetRef = useRef(0)
  const startY = useRef(null)
  const isOverscrolling = useRef(false)
  const gestureDecided = useRef(false)

  useEffect(() => {
    overscrollOffsetRef.current = overscrollOffset
  }, [overscrollOffset])

  useEffect(() => {
    const scrollEl = scrollRef.current
    if (!scrollEl) return

    const isAtBottom = () => {
      const { scrollTop, scrollHeight, clientHeight } = scrollEl
      return scrollHeight - scrollTop - clientHeight < 1
    }

    const handleTouchStart = (e) => {
      gestureDecided.current = false
      if (isAtBottom()) {
        startY.current = e.touches[0].clientY
      }
    }

    const handleTouchMove = (e) => {
      if (startY.current === null) return

      const deltaY = startY.current - e.touches[0].clientY

      // First significant movement decides if this is our gesture
      if (!gestureDecided.current && Math.abs(deltaY) > 5) {
        gestureDecided.current = true
        if (deltaY <= 0) {
          // Downward movement - not our gesture, bail out entirely
          startY.current = null
          return
        }
      }

      if (deltaY > 0 && isAtBottom()) {
        e.preventDefault()
        isOverscrolling.current = true
        setOverscrollOffset(Math.min(deltaY * 0.5, threshold * 1.5))
      } else if (deltaY < -10) {
        startY.current = null
        isOverscrolling.current = false
        setOverscrollOffset(0)
      }
    }

    const handleTouchEnd = () => {
      if (isOverscrolling.current && overscrollOffsetRef.current >= threshold * 0.5) {
        onComplete()
      }
      setOverscrollOffset(0)
      startY.current = null
      isOverscrolling.current = false
      gestureDecided.current = false
    }

    scrollEl.addEventListener('touchstart', handleTouchStart, { passive: true })
    scrollEl.addEventListener('touchmove', handleTouchMove, { passive: false })
    scrollEl.addEventListener('touchend', handleTouchEnd, { passive: true })

    return () => {
      scrollEl.removeEventListener('touchstart', handleTouchStart)
      scrollEl.removeEventListener('touchmove', handleTouchMove)
      scrollEl.removeEventListener('touchend', handleTouchEnd)
    }
  }, [scrollRef, onComplete, threshold])

  const progress = Math.min(overscrollOffset / (threshold * 0.5), 1)

  return {
    overscrollOffset,
    isOverscrolling: overscrollOffset > 0,
    progress,
    isComplete: progress >= 1
  }
}
