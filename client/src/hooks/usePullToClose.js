import { useEffect, useRef, useState } from 'react'

export function usePullToClose({ containerRef, scrollRef, onClose, threshold = 80 }) {
  const [pullOffset, setPullOffset] = useState(0)
  const pullOffsetRef = useRef(0)
  const startY = useRef(null)
  const isPulling = useRef(false)

  useEffect(() => {
    pullOffsetRef.current = pullOffset
  }, [pullOffset])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleTouchStart = (e) => {
      const touchedScrollArea = scrollRef.current?.contains(e.target)
      const scrollEl = scrollRef.current
      const isAtTop = scrollEl?.scrollTop === 0
      const isAtBottom = scrollEl && (scrollEl.scrollHeight - scrollEl.scrollTop - scrollEl.clientHeight < 1)
      if (!touchedScrollArea || isAtTop || isAtBottom) {
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

    container.addEventListener('touchstart', handleTouchStart, { passive: true })
    container.addEventListener('touchmove', handleTouchMove, { passive: false })
    container.addEventListener('touchend', handleTouchEnd, { passive: true })

    return () => {
      container.removeEventListener('touchstart', handleTouchStart)
      container.removeEventListener('touchmove', handleTouchMove)
      container.removeEventListener('touchend', handleTouchEnd)
    }
  }, [containerRef, scrollRef, onClose, threshold])

  return { pullOffset }
}
