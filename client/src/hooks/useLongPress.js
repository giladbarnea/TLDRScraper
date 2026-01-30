import { useCallback, useRef } from 'react'

export function useLongPress(onLongPress, { threshold = 500, disabled = false } = {}) {
  const timerRef = useRef(null)
  const startPosRef = useRef(null)
  const activePointerIdRef = useRef(null)
  const didLongPressRef = useRef(false)

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const start = useCallback((pointerId, clientX, clientY) => {
    if (disabled) return

    activePointerIdRef.current = pointerId
    startPosRef.current = { x: clientX, y: clientY }
    didLongPressRef.current = false

    clearTimer()
    timerRef.current = setTimeout(() => {
      didLongPressRef.current = true
      onLongPress()
    }, threshold)
  }, [disabled, clearTimer, onLongPress, threshold])

  const move = useCallback((pointerId, clientX, clientY) => {
    if (activePointerIdRef.current !== pointerId) return
    if (!startPosRef.current) return

    const dx = Math.abs(clientX - startPosRef.current.x)
    const dy = Math.abs(clientY - startPosRef.current.y)

    if (dx > 10 || dy > 10) {
      clearTimer()
      startPosRef.current = null
    }
  }, [clearTimer])

  const end = useCallback((pointerId) => {
    if (activePointerIdRef.current !== pointerId) return
    clearTimer()
    startPosRef.current = null
    activePointerIdRef.current = null
  }, [clearTimer])

  const onPointerDown = useCallback((e) => {
    if (e.pointerType === 'mouse' && e.button !== 0) return
    start(e.pointerId, e.clientX, e.clientY)
  }, [start])

  const onPointerMove = useCallback((e) => {
    move(e.pointerId, e.clientX, e.clientY)
  }, [move])

  const onPointerUp = useCallback((e) => {
    end(e.pointerId)
  }, [end])

  const onPointerCancel = useCallback((e) => {
    end(e.pointerId)
    didLongPressRef.current = false
  }, [end])

  return {
    handlers: {
      onPointerDown,
      onPointerMove,
      onPointerUp,
      onPointerCancel,
    },
    didLongPressRef,
  }
}
