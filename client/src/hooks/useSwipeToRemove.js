import { useAnimation } from 'framer-motion'
import { useCallback, useEffect, useReducer, useRef } from 'react'
import { logTransition } from '../lib/stateTransitionLogger'
import {
  createInitialGestureState,
  GestureEventType,
  GestureMode,
  reduceGesture,
} from '../reducers/gestureReducer'

export function useSwipeToRemove({ isRemoved, stateLoading, onSwipeComplete, url }) {
  const reducerWrapper = useCallback((currentState, event) => {
    if (event?.type === '__REPLACE_STATE__') {
      return event.nextState
    }
    return reduceGesture(currentState, event).state
  }, [])

  const [state, rawDispatch] = useReducer(reducerWrapper, undefined, createInitialGestureState)
  const controls = useAnimation()
  const previousModeRef = useRef(state.mode)

  const canDrag = !isRemoved && !stateLoading

  useEffect(() => {
    controls.start({
      opacity: stateLoading ? 0.4 : isRemoved ? 0.5 : 1,
      filter: stateLoading || isRemoved ? 'grayscale(100%)' : 'grayscale(0%)',
      x: 0,
    })
  }, [isRemoved, stateLoading, controls])

  useEffect(() => {
    const previousMode = previousModeRef.current
    if (previousMode !== state.mode) {
      logTransition('gesture', url, previousMode, state.mode)
      previousModeRef.current = state.mode
    }
  }, [state.mode, url])

  const dispatchWithDecision = useCallback((event) => {
    const result = reduceGesture(state, event)
    rawDispatch({ type: '__REPLACE_STATE__', nextState: result.state })
    return result.decision
  }, [state, rawDispatch])

  const handleDragStart = useCallback(() => {
    rawDispatch({ type: GestureEventType.DRAG_START })
  }, [rawDispatch])

  const handleDragEnd = useCallback(async (_event, info) => {
    try {
      const { offset, velocity } = info
      const decision = dispatchWithDecision({
        type: GestureEventType.DRAG_END,
        offsetX: offset.x,
        velocityX: velocity.x,
      })

      if (decision?.shouldComplete) {
        await controls.start({
          x: -window.innerWidth,
          opacity: 0,
          transition: { duration: 0.2, ease: "easeOut" }
        })
        onSwipeComplete()
      } else {
        controls.start({ x: 0 })
      }
    } catch (error) {
      dispatchWithDecision({
        type: GestureEventType.DRAG_ERROR,
        message: `Drag error: ${error.message}`,
      })
      controls.start({ x: 0 })
    }
  }, [controls, dispatchWithDecision, onSwipeComplete])

  const clearDragError = useCallback(() => {
    rawDispatch({ type: GestureEventType.CLEAR_ERROR })
  }, [rawDispatch])

  return {
    isDragging: state.mode === GestureMode.DRAGGING,
    dragError: state.errorMessage,
    clearDragError,
    controls,
    canDrag,
    handleDragStart,
    handleDragEnd,
  }
}
