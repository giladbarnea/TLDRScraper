export const GestureMode = Object.freeze({
  IDLE: 'idle',
  DRAGGING: 'dragging',
})

export const GestureEventType = Object.freeze({
  DRAG_START: 'DRAG_START',
  DRAG_END: 'DRAG_END',
  DRAG_ERROR: 'DRAG_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
})

export function createInitialGestureState() {
  return {
    mode: GestureMode.IDLE,
    errorMessage: null,
  }
}

export function reduceGesture(state, event) {
  switch (event.type) {
    case GestureEventType.DRAG_START:
      return {
        state: {
          ...state,
          mode: GestureMode.DRAGGING,
          errorMessage: null,
        },
        decision: null,
      }
    case GestureEventType.DRAG_END: {
      const swipeThreshold = -100
      const velocityThreshold = -300
      const shouldComplete = event.offsetX < swipeThreshold || event.velocityX < velocityThreshold
      return {
        state: {
          ...state,
          mode: GestureMode.IDLE,
          errorMessage: null,
        },
        decision: { shouldComplete },
      }
    }
    case GestureEventType.DRAG_ERROR:
      return {
        state: {
          ...state,
          mode: GestureMode.IDLE,
          errorMessage: event.message,
        },
        decision: null,
      }
    case GestureEventType.CLEAR_ERROR:
      return {
        state: {
          ...state,
          errorMessage: null,
        },
        decision: null,
      }
    default:
      return { state, decision: null }
  }
}
