import { useCallback, useRef, useState } from 'react'

export function usePullToClose({ scrollRef, onClose, threshold = 80 }) {
  const [pullOffset, setPullOffset] = useState(0)
  const startY = useRef(null)
  const isPulling = useRef(false)

  const handleTouchStart = useCallback((e) => {
    if (scrollRef.current?.scrollTop === 0) {
      startY.current = e.touches[0].clientY
    }
  }, [scrollRef])

  const handleTouchMove = useCallback((e) => {
    if (startY.current === null) return

    const currentY = e.touches[0].clientY
    const diff = currentY - startY.current

    if (diff > 0) {
      isPulling.current = true
      e.preventDefault()
      setPullOffset(diff * 0.5)
    } else if (diff < -10) {
      startY.current = null
      isPulling.current = false
      setPullOffset(0)
    }
  }, [])

  const handleTouchEnd = useCallback(() => {
    if (isPulling.current && pullOffset > threshold) {
      onClose()
    }
    setPullOffset(0)
    startY.current = null
    isPulling.current = false
  }, [pullOffset, threshold, onClose])

  return {
    pullOffset,
    handlers: {
      onTouchStart: handleTouchStart,
      onTouchMove: handleTouchMove,
      onTouchEnd: handleTouchEnd,
    }
  }
}
