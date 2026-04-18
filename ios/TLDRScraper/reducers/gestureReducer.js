export const GestureMode = Object.freeze({
  IDLE: 'idle',
  DRAGGING: 'dragging',
})

export const GestureEventType = Object.freeze({
  DRAG_STARTED: 'DRAG_STARTED',
  DRAG_FINISHED: 'DRAG_FINISHED',
  DRAG_FAILED: 'DRAG_FAILED',
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
    case GestureEventType.DRAG_STARTED:
      return {
        ...state,
        mode: GestureMode.DRAGGING,
        errorMessage: null,
      }

    case GestureEventType.DRAG_FINISHED:
      return {
        ...state,
        mode: GestureMode.IDLE,
      }

    case GestureEventType.DRAG_FAILED:
      return {
        ...state,
        mode: GestureMode.IDLE,
        errorMessage: event.errorMessage,
      }

    case GestureEventType.CLEAR_ERROR:
      return {
        ...state,
        errorMessage: null,
      }

    default:
      return state
  }
}
