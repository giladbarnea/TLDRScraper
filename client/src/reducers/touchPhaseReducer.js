export const TouchPhase = Object.freeze({
  IDLE: 'idle',
  PRESSED: 'pressed',
  RELEASED: 'released',
})

export const TouchPhaseEventType = Object.freeze({
  POINTER_DOWN: 'POINTER_DOWN',
  MOVE_EXCEEDED: 'MOVE_EXCEEDED',
  AUTO_CANCEL: 'AUTO_CANCEL',
  POINTER_CANCEL: 'POINTER_CANCEL',
  POINTER_UP: 'POINTER_UP',
  RELEASE_EXPIRED: 'RELEASE_EXPIRED',
})

/**
 * Pure reducer for the touch phase state machine (Domain E).
 * @example
 * reduceTouchPhase('idle', { type: 'POINTER_DOWN' })
 * // => 'pressed'
 */
export function reduceTouchPhase(currentPhase, event) {
  switch (event.type) {
    case TouchPhaseEventType.POINTER_DOWN:
      if (currentPhase === TouchPhase.IDLE || currentPhase === TouchPhase.RELEASED)
        return TouchPhase.PRESSED
      return currentPhase

    case TouchPhaseEventType.MOVE_EXCEEDED:
    case TouchPhaseEventType.AUTO_CANCEL:
    case TouchPhaseEventType.POINTER_CANCEL:
      if (currentPhase === TouchPhase.PRESSED) return TouchPhase.IDLE
      return currentPhase

    case TouchPhaseEventType.POINTER_UP:
      if (currentPhase === TouchPhase.PRESSED) return TouchPhase.RELEASED
      return currentPhase

    case TouchPhaseEventType.RELEASE_EXPIRED:
      if (currentPhase === TouchPhase.RELEASED) return TouchPhase.IDLE
      return currentPhase

    default:
      return currentPhase
  }
}
