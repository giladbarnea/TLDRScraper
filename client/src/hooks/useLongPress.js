import { useCallback, useRef } from 'react'

export function useLongPress(onLongPress, { threshold = 500, disabled = false } = {}) {
  const timerRef = useRef(null)
  const startPosRef = useRef(null)
  const isLongPressRef = useRef(false)
  const ignoreMouseRef = useRef(false)
  const mouseBlockTimerRef = useRef(null)

  const clear = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
    startPosRef.current = null
  }, [])

  const scheduleMouseReset = useCallback(() => {
    if (mouseBlockTimerRef.current) {
      clearTimeout(mouseBlockTimerRef.current)
    }
    mouseBlockTimerRef.current = setTimeout(() => {
      ignoreMouseRef.current = false
      mouseBlockTimerRef.current = null
    }, threshold + 100)
  }, [threshold])

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
    ignoreMouseRef.current = true
    scheduleMouseReset()
    const touch = e.touches[0]
    start(touch.clientX, touch.clientY)
  }, [start, scheduleMouseReset])

  const onTouchMove = useCallback((e) => {
    const touch = e.touches[0]
    move(touch.clientX, touch.clientY)
  }, [move])

  const onTouchEnd = useCallback(() => {
    clear()
    scheduleMouseReset()
  }, [clear, scheduleMouseReset])

  const onMouseDown = useCallback((e) => {
    if (ignoreMouseRef.current) return
    e.stopPropagation()
    start(e.clientX, e.clientY)
  }, [start])

  const onMouseMove = useCallback((e) => {
    if (ignoreMouseRef.current) return
    move(e.clientX, e.clientY)
  }, [move])

  const onMouseUp = useCallback(() => {
    if (ignoreMouseRef.current) return
    clear()
  }, [clear])

  const onMouseLeave = useCallback(() => {
    if (ignoreMouseRef.current) return
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
