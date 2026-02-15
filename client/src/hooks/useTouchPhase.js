import { useCallback, useEffect, useRef, useState } from 'react'
import { LONG_PRESS_THRESHOLD_MS, POINTER_MOVE_THRESHOLD_PX, RELEASE_DURATION_MS } from '../lib/interactionConstants'
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
  const cancelTimerRef = useRef(null)
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
      if (cancelTimerRef.current) clearTimeout(cancelTimerRef.current)
      if (releaseTimerRef.current) clearTimeout(releaseTimerRef.current)
    }
  }, [])

  const reset = useCallback(() => {
    pointerIdRef.current = null
    startPosRef.current = null
  }, [])

  const onPointerDown = useCallback((e) => {
    console.log('[touch-phase] onPointerDown fired', e.pointerType, e.pointerId, { isSelectMode, isRemoved, isDragging })
    if (e.pointerType === 'mouse' && e.button !== 0) return
    if (isSelectMode || isRemoved || isDragging) return

    if (cancelTimerRef.current) {
      clearTimeout(cancelTimerRef.current)
      cancelTimerRef.current = null
    }
    if (releaseTimerRef.current) {
      clearTimeout(releaseTimerRef.current)
      releaseTimerRef.current = null
    }

    pointerIdRef.current = e.pointerId
    startPosRef.current = { x: e.clientX, y: e.clientY }

    dispatch(TouchPhaseEventType.POINTER_DOWN)

    cancelTimerRef.current = setTimeout(() => {
      dispatch(TouchPhaseEventType.AUTO_CANCEL)
      reset()
    }, LONG_PRESS_THRESHOLD_MS)
  }, [isSelectMode, isRemoved, isDragging, dispatch, reset])

  const onPointerMove = useCallback((e) => {
    if (pointerIdRef.current !== e.pointerId) return
    if (!startPosRef.current) return

    const dx = Math.abs(e.clientX - startPosRef.current.x)
    const dy = Math.abs(e.clientY - startPosRef.current.y)

    if (dx > POINTER_MOVE_THRESHOLD_PX || dy > POINTER_MOVE_THRESHOLD_PX) {
      if (cancelTimerRef.current) {
        clearTimeout(cancelTimerRef.current)
        cancelTimerRef.current = null
      }
      dispatch(TouchPhaseEventType.MOVE_EXCEEDED)
      reset()
    }
  }, [dispatch, reset])

  const onPointerUp = useCallback((e) => {
    if (pointerIdRef.current !== e.pointerId) return

    if (cancelTimerRef.current) {
      clearTimeout(cancelTimerRef.current)
      cancelTimerRef.current = null
    }

    dispatch(TouchPhaseEventType.POINTER_UP)

    releaseTimerRef.current = setTimeout(() => {
      dispatch(TouchPhaseEventType.RELEASE_EXPIRED)
    }, RELEASE_DURATION_MS)

    reset()
  }, [dispatch, reset])

  const onPointerCancel = useCallback((e) => {
    if (pointerIdRef.current !== e.pointerId) return

    if (cancelTimerRef.current) {
      clearTimeout(cancelTimerRef.current)
      cancelTimerRef.current = null
    }
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
