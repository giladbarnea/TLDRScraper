export const MobileSelectionMenuEventType = Object.freeze({
  TOUCH_STARTED: 'TOUCH_STARTED',
  TOUCH_ENDED: 'TOUCH_ENDED',
  SELECTION_OBSERVED: 'SELECTION_OBSERVED',
  SELECTION_CLEARED: 'SELECTION_CLEARED',
  MENU_CLOSED: 'MENU_CLOSED',
})

export const MobileSelectionMenuDecisionType = Object.freeze({
  NONE: 'NONE',
  OPEN_MENU: 'OPEN_MENU',
  CLOSE_MENU: 'CLOSE_MENU',
})

const NONE_DECISION = Object.freeze({
  type: MobileSelectionMenuDecisionType.NONE,
})

function openMenuDecision(selection) {
  return {
    type: MobileSelectionMenuDecisionType.OPEN_MENU,
    selection,
  }
}

const CLOSE_MENU_DECISION = Object.freeze({
  type: MobileSelectionMenuDecisionType.CLOSE_MENU,
})

export function createInitialMobileSelectionMenuState() {
  return {
    isTouching: false,
    isOpen: false,
    selection: null,
  }
}

const MOBILE_SELECTION_TRANSITIONS = Object.freeze({
  [MobileSelectionMenuEventType.TOUCH_STARTED]: (state) => ({
    state: { ...state, isTouching: true },
    decision: NONE_DECISION,
  }),

  [MobileSelectionMenuEventType.TOUCH_ENDED]: (state, event) => {
    if (!event.selection) {
      return {
        state: { ...state, isTouching: false },
        decision: NONE_DECISION,
      }
    }

    return {
      state: {
        isTouching: false,
        isOpen: true,
        selection: event.selection,
      },
      decision: openMenuDecision(event.selection),
    }
  },

  [MobileSelectionMenuEventType.SELECTION_OBSERVED]: (state, event) => {
    if (state.isTouching) {
      return {
        state: { ...state, selection: event.selection },
        decision: NONE_DECISION,
      }
    }

    return {
      state: {
        isTouching: false,
        isOpen: true,
        selection: event.selection,
      },
      decision: openMenuDecision(event.selection),
    }
  },

  [MobileSelectionMenuEventType.SELECTION_CLEARED]: (state) => {
    if (state.isTouching) {
      return {
        state: {
          ...state,
          selection: state.isOpen ? state.selection : null,
        },
        decision: NONE_DECISION,
      }
    }

    if (!state.isOpen) {
      return {
        state: createInitialMobileSelectionMenuState(),
        decision: NONE_DECISION,
      }
    }

    return {
      state: createInitialMobileSelectionMenuState(),
      decision: CLOSE_MENU_DECISION,
    }
  },

  [MobileSelectionMenuEventType.MENU_CLOSED]: () => ({
    state: createInitialMobileSelectionMenuState(),
    decision: NONE_DECISION,
  }),
})

export function reduceMobileSelectionMenu(state, event) {
  const transition = MOBILE_SELECTION_TRANSITIONS[event.type]
  if (!transition) return { state, decision: NONE_DECISION }
  return transition(state, event)
}
