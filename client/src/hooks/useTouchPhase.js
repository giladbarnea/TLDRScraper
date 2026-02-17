import { useCallback, useEffect, useRef, useState } from 'react'
import { POINTER_MOVE_THRESHOLD_PX, RELEASE_DURATION_MS } from '../lib/interactionConstants'
import { logTransition } from '../lib/stateTransitionLogger'
import { reduceTouchPhase, TouchPhase, TouchPhaseEventType } from '../reducers/touchPhaseReducer'

/**
 * Tracks the pointer lifecycle on a card as a three-state machine: idle → pressed → released → idle.
 * Purely additive — does not modify interaction or summary data flows.
 */
export function useTouchPhase({ isSelectMode, isRemoved, isDragging, url }) {
  const [touchPhase, setTouchPhase] = useState(TouchPhase.IDLE)
  const pointerIdRef = useRef(null)
  const startPosRef = useRef(null)
  const releaseTimerRef = useRef(null)
  const previousPhaseRef = useRef(TouchPhase.IDLE)

  const dispatch = useCallback((eventType) => {
    setTouchPhase(current => reduceTouchPhase(current, { type: eventType }))
  }, [])

  useEffect(() => {
    if (previousPhaseRef.current !== touchPhase) {
      logTransition('touch-phase', url, previousPhaseRef.current, touchPhase)
      previousPhaseRef.current = touchPhase
    }
  }, [touchPhase, url])

  useEffect(() => {
    return () => {
      if (releaseTimerRef.current) clearTimeout(releaseTimerRef.current)
    }
  }, [])

  const reset = useCallback(() => {
    pointerIdRef.current = null
    startPosRef.current = null
  }, [])

  const onPointerDown = useCallback((e) => {
    logTransition('touch-phase', url, 'pointerDown', `id=${e.pointerId} type=${e.pointerType}`, `guards: select=${isSelectMode} removed=${isRemoved} drag=${isDragging}`)
    if (e.pointerType === 'mouse' && e.button !== 0) return
    if (isSelectMode || isRemoved || isDragging) return

    if (releaseTimerRef.current) {
      clearTimeout(releaseTimerRef.current)
      releaseTimerRef.current = null
    }

    pointerIdRef.current = e.pointerId
    startPosRef.current = { x: e.clientX, y: e.clientY }

    const rect = e.currentTarget.getBoundingClientRect()
    const angleDeg = Math.atan2(
      e.clientY - (rect.top + rect.height / 2),
      e.clientX - (rect.left + rect.width / 2)
    ) * (180 / Math.PI)
    e.currentTarget.style.setProperty('--touch-angle', `${angleDeg + 90}deg`)

    dispatch(TouchPhaseEventType.POINTER_DOWN)
  }, [isSelectMode, isRemoved, isDragging, dispatch, reset])

  const onPointerMove = useCallback((e) => {
    if (pointerIdRef.current !== e.pointerId) return
    if (!startPosRef.current) return

    const dx = Math.abs(e.clientX - startPosRef.current.x)
    const dy = Math.abs(e.clientY - startPosRef.current.y)

    if (dx > POINTER_MOVE_THRESHOLD_PX || dy > POINTER_MOVE_THRESHOLD_PX) {
      dispatch(TouchPhaseEventType.MOVE_EXCEEDED)
      reset()
    }
  }, [dispatch, reset])

  const onPointerUp = useCallback((e) => {
    logTransition('touch-phase', url, 'pointerUp', `id=${e.pointerId}`, `tracked=${pointerIdRef.current}`)
    if (pointerIdRef.current !== e.pointerId) return

    dispatch(TouchPhaseEventType.POINTER_UP)

    releaseTimerRef.current = setTimeout(() => {
      dispatch(TouchPhaseEventType.RELEASE_EXPIRED)
    }, RELEASE_DURATION_MS)

    reset()
  }, [dispatch, reset])

  const onPointerCancel = useCallback((e) => {
    logTransition('touch-phase', url, 'pointerCancel', `id=${e.pointerId}`, `tracked=${pointerIdRef.current}`)
    if (pointerIdRef.current !== e.pointerId) return

    if (releaseTimerRef.current) {
      clearTimeout(releaseTimerRef.current)
      releaseTimerRef.current = null
    }

    dispatch(TouchPhaseEventType.POINTER_CANCEL)
    reset()
  }, [dispatch, reset])

  return {
    touchPhase,
    pointerHandlers: {
      onPointerDown,
      onPointerMove,
      onPointerUp,
      onPointerCancel,
    },
  }
}
