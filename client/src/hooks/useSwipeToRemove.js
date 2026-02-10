import { useAnimation } from 'framer-motion'
import { useEffect, useReducer } from 'react'
import { logTransition } from '../lib/stateTransitionLogger'
import {
  createInitialGestureState,
  GestureEventType,
  GestureMode,
  reduceGesture,
} from '../reducers/gestureReducer'

export function useSwipeToRemove({ isRemoved, stateLoading, onSwipeComplete, url }) {
  const [gestureState, dispatchGestureEvent] = useReducer(
    reduceGesture,
    undefined,
    createInitialGestureState,
  )
  const controls = useAnimation()

  const canDrag = !isRemoved && !stateLoading

  useEffect(() => {
    controls.start({
      opacity: stateLoading ? 0.4 : isRemoved ? 0.5 : 1,
      filter: stateLoading || isRemoved ? 'grayscale(100%)' : 'grayscale(0%)',
      x: 0,
    })
  }, [isRemoved, stateLoading, controls])

  const handleDragStart = () => {
    logTransition('gesture', url, GestureMode.IDLE, GestureMode.DRAGGING)
    dispatchGestureEvent({ type: GestureEventType.DRAG_STARTED })
  }

  const handleDragEnd = async (_event, info) => {
    logTransition('gesture', url, GestureMode.DRAGGING, GestureMode.IDLE)
    dispatchGestureEvent({ type: GestureEventType.DRAG_FINISHED })

    try {
      const { offset, velocity } = info
      const swipeThreshold = -100
      const velocityThreshold = -300

      if (offset.x < swipeThreshold || velocity.x < velocityThreshold) {
        await controls.start({
          x: -window.innerWidth,
          opacity: 0,
          transition: { duration: 0.2, ease: 'easeOut' },
        })
        onSwipeComplete()
      } else {
        controls.start({ x: 0 })
      }
    } catch (error) {
      dispatchGestureEvent({
        type: GestureEventType.DRAG_FAILED,
        errorMessage: `Drag error: ${error.message}`,
      })
      controls.start({ x: 0 })
    }
  }

  const clearDragError = () => dispatchGestureEvent({ type: GestureEventType.CLEAR_ERROR })

  return {
    isDragging: gestureState.mode === GestureMode.DRAGGING,
    dragError: gestureState.errorMessage,
    clearDragError,
    controls,
    canDrag,
    handleDragStart,
    handleDragEnd,
  }
}
