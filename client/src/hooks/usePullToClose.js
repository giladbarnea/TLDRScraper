import { useEffect, useRef } from 'react'
import { useTrackedState } from './useTrackedState'

export function usePullToClose({ containerRef, scrollRef, onClose, threshold = 80, enabled = true }) {
  const [pullOffset, setPullOffset, pullOffsetRef] = useTrackedState(0)
  const startY = useRef(null)
  const isPulling = useRef(false)

  useEffect(() => {
    if (!enabled) {
      setPullOffset(0)
      startY.current = null
      isPulling.current = false
      return
    }

    const container = containerRef.current
    if (!container) return

    function handleTouchStart(event) {
      const touchedScrollArea = scrollRef.current?.contains(event.target)
      const scrollTop = scrollRef.current?.scrollTop
      if (!touchedScrollArea || scrollTop === 0) {
        startY.current = event.touches[0].clientY
      }
    }

    function handleTouchMove(event) {
      if (startY.current === null) return

      const difference = event.touches[0].clientY - startY.current

      if (difference > 0) {
        event.preventDefault()
        isPulling.current = true
        setPullOffset(difference * 0.5)
        return
      }

      if (difference < -10) {
        startY.current = null
        isPulling.current = false
        setPullOffset(0)
      }
    }

    function handleTouchEnd() {
      if (isPulling.current && pullOffsetRef.current > threshold) {
        onClose()
      }
      setPullOffset(0)
      startY.current = null
      isPulling.current = false
    }

    container.addEventListener('touchstart', handleTouchStart, { passive: true })
    container.addEventListener('touchmove', handleTouchMove, { passive: false })
    container.addEventListener('touchend', handleTouchEnd, { passive: true })

    return () => {
      container.removeEventListener('touchstart', handleTouchStart)
      container.removeEventListener('touchmove', handleTouchMove)
      container.removeEventListener('touchend', handleTouchEnd)
    }
  }, [containerRef, enabled, onClose, pullOffsetRef, scrollRef, setPullOffset, threshold])

  return { pullOffset }
}
