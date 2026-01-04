import { useEffect, useRef, useState } from 'react'

export function usePullToClose({ scrollRef, onClose, threshold = 80 }) {
  const [pullOffset, setPullOffset] = useState(0)
  const pullOffsetRef = useRef(0)
  const startY = useRef(null)
  const isPulling = useRef(false)

  useEffect(() => {
    pullOffsetRef.current = pullOffset
  }, [pullOffset])

  useEffect(() => {
    const element = scrollRef.current
    if (!element) return

    const handleTouchStart = (e) => {
      if (element.scrollTop === 0) {
        startY.current = e.touches[0].clientY
      }
    }

    const handleTouchMove = (e) => {
      if (startY.current === null) return

      const diff = e.touches[0].clientY - startY.current

      if (diff > 0) {
        e.preventDefault()
        isPulling.current = true
        setPullOffset(diff * 0.5)
      } else if (diff < -10) {
        startY.current = null
        isPulling.current = false
        setPullOffset(0)
      }
    }

    const handleTouchEnd = () => {
      if (isPulling.current && pullOffsetRef.current > threshold) {
        onClose()
      }
      setPullOffset(0)
      startY.current = null
      isPulling.current = false
    }

    element.addEventListener('touchstart', handleTouchStart, { passive: true })
    element.addEventListener('touchmove', handleTouchMove, { passive: false })
    element.addEventListener('touchend', handleTouchEnd, { passive: true })

    return () => {
      element.removeEventListener('touchstart', handleTouchStart)
      element.removeEventListener('touchmove', handleTouchMove)
      element.removeEventListener('touchend', handleTouchEnd)
    }
  }, [scrollRef, onClose, threshold])

  return { pullOffset }
}
