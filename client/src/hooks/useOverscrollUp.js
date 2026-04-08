import { useEffect, useRef } from 'react'
import { useTrackedState } from './useTrackedState'

export function useOverscrollUp({ scrollRef, onComplete, threshold = 60, enabled = true }) {
  const [overscrollOffset, setOverscrollOffset, overscrollOffsetRef] = useTrackedState(0)
  const startY = useRef(null)
  const isOverscrolling = useRef(false)

  useEffect(() => {
    if (!enabled) {
      setOverscrollOffset(0)
      startY.current = null
      isOverscrolling.current = false
      return
    }

    const scrollElement = scrollRef.current
    if (!scrollElement) return

    function isAtBottom() {
      const { scrollTop, scrollHeight, clientHeight } = scrollElement
      return scrollHeight - scrollTop - clientHeight < 1
    }

    function handleTouchStart(event) {
      if (isAtBottom()) {
        startY.current = event.touches[0].clientY
      }
    }

    function handleTouchMove(event) {
      if (startY.current === null) return

      const deltaY = startY.current - event.touches[0].clientY

      if (deltaY > 0 && isAtBottom()) {
        event.preventDefault()
        isOverscrolling.current = true
        setOverscrollOffset(Math.min(deltaY * 0.5, threshold * 1.5))
        return
      }

      if (deltaY < -10) {
        startY.current = null
        isOverscrolling.current = false
        setOverscrollOffset(0)
      }
    }

    function handleTouchEnd() {
      if (isOverscrolling.current && overscrollOffsetRef.current >= threshold * 0.5) {
        onComplete()
      }
      setOverscrollOffset(0)
      startY.current = null
      isOverscrolling.current = false
    }

    scrollElement.addEventListener('touchstart', handleTouchStart, { passive: true })
    scrollElement.addEventListener('touchmove', handleTouchMove, { passive: false })
    scrollElement.addEventListener('touchend', handleTouchEnd, { passive: true })

    return () => {
      scrollElement.removeEventListener('touchstart', handleTouchStart)
      scrollElement.removeEventListener('touchmove', handleTouchMove)
      scrollElement.removeEventListener('touchend', handleTouchEnd)
    }
  }, [enabled, onComplete, overscrollOffsetRef, scrollRef, setOverscrollOffset, threshold])

  const progress = Math.min(overscrollOffset / (threshold * 0.5), 1)

  return {
    overscrollOffset,
    isOverscrolling: overscrollOffset > 0,
    progress,
    isComplete: progress >= 1,
  }
}
