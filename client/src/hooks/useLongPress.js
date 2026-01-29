import { useCallback, useRef } from 'react'

export function useLongPress(onLongPress, { threshold = 500, disabled = false } = {}) {
  const timerRef = useRef(null)
  const startPosRef = useRef(null)
  const isLongPressRef = useRef(false)

  const clear = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
    startPosRef.current = null
  }, [])

  const start = useCallback((clientX, clientY) => {
    if (disabled) return

    isLongPressRef.current = false
    startPosRef.current = { x: clientX, y: clientY }

    timerRef.current = setTimeout(() => {
      isLongPressRef.current = true
      onLongPress()
    }, threshold)
  }, [disabled, onLongPress, threshold])

  const move = useCallback((clientX, clientY) => {
    if (!startPosRef.current) return

    const dx = Math.abs(clientX - startPosRef.current.x)
    const dy = Math.abs(clientY - startPosRef.current.y)

    if (dx > 10 || dy > 10) {
      clear()
    }
  }, [clear])

  const onTouchStart = useCallback((e) => {
    e.stopPropagation()
    const touch = e.touches[0]
    start(touch.clientX, touch.clientY)
  }, [start])

  const onTouchMove = useCallback((e) => {
    const touch = e.touches[0]
    move(touch.clientX, touch.clientY)
  }, [move])

  const onTouchEnd = useCallback(() => {
    clear()
  }, [clear])

  const onMouseDown = useCallback((e) => {
    e.stopPropagation()
    start(e.clientX, e.clientY)
  }, [start])

  const onMouseMove = useCallback((e) => {
    move(e.clientX, e.clientY)
  }, [move])

  const onMouseUp = useCallback(() => {
    clear()
  }, [clear])

  const onMouseLeave = useCallback(() => {
    clear()
  }, [clear])

  return {
    handlers: {
      onTouchStart,
      onTouchMove,
      onTouchEnd,
      onMouseDown,
      onMouseMove,
      onMouseUp,
      onMouseLeave,
    },
    isLongPressRef,
  }
}
