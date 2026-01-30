import { createContext, useCallback, useContext, useEffect, useMemo, useReducer } from 'react'
import {
  createInitialInteractionState,
  interactionReduce,
  InteractionEventType,
} from '../reducers/interactionReducer'

const InteractionContext = createContext(null)

const EXPANDED_STORAGE_KEY = 'expandedContainers:v1'
const INTERNAL = Object.freeze({
  REPLACE_STATE: '__REPLACE_STATE__',
})

function loadExpandedFromStorage() {
  try {
    const raw = localStorage.getItem(EXPANDED_STORAGE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    return new Set(Array.isArray(arr) ? arr : [])
  } catch {
    return new Set()
  }
}

function saveExpandedToStorage(expandedSet) {
  try {
    localStorage.setItem(EXPANDED_STORAGE_KEY, JSON.stringify([...expandedSet]))
  } catch {
    return
  }
}

function init() {
  const initialState = createInitialInteractionState()
  initialState.expandedContainerIds = loadExpandedFromStorage()
  return initialState
}

export function InteractionProvider({ children }) {
  const reducerWrapper = useCallback((currentState, event) => {
    if (event?.type === INTERNAL.REPLACE_STATE) {
      return event.nextState
    }
    return interactionReduce(currentState, event).state
  }, [])

  const [state, rawDispatch] = useReducer(reducerWrapper, undefined, init)

  useEffect(() => {
    saveExpandedToStorage(state.expandedContainerIds)
  }, [state.expandedContainerIds])

  const isSelectMode = state.selectedIds.size > 0

  const dispatchWithDecision = useCallback((event) => {
    const result = interactionReduce(state, event)
    rawDispatch({ type: INTERNAL.REPLACE_STATE, nextState: result.state })
    return result.decision
  }, [state, rawDispatch])

  const registerDisabled = useCallback((id, isDisabled) => {
    rawDispatch({ type: InteractionEventType.REGISTER_DISABLED, id, isDisabled })
  }, [rawDispatch])

  const clearSelection = useCallback(() => {
    rawDispatch({ type: InteractionEventType.CLEAR_SELECTION })
  }, [rawDispatch])

  const setExpanded = useCallback((containerId, expanded) => {
    rawDispatch({ type: InteractionEventType.SET_EXPANDED, containerId, expanded })
  }, [rawDispatch])

  const isSelected = useCallback((id) => state.selectedIds.has(id), [state.selectedIds])

  const isExpanded = useCallback((containerId) => {
    return state.expandedContainerIds.has(containerId)
  }, [state.expandedContainerIds])

  const itemLongPress = useCallback((itemId) => {
    rawDispatch({ type: InteractionEventType.ITEM_LONG_PRESS, itemId })
  }, [rawDispatch])

  const containerLongPress = useCallback((containerId, childIds) => {
    rawDispatch({ type: InteractionEventType.CONTAINER_LONG_PRESS, containerId, childIds })
  }, [rawDispatch])

  const containerShortPress = useCallback((containerId) => {
    rawDispatch({ type: InteractionEventType.CONTAINER_SHORT_PRESS, containerId })
  }, [rawDispatch])

  const itemShortPress = useCallback((itemId) => {
    const decision = dispatchWithDecision({ type: InteractionEventType.ITEM_SHORT_PRESS, itemId })
    return Boolean(decision?.shouldOpenItem)
  }, [dispatchWithDecision])

  const value = useMemo(() => ({
    selectedIds: state.selectedIds,
    isSelectMode,
    isSelected,
    isExpanded,
    registerDisabled,
    clearSelection,
    setExpanded,
    itemShortPress,
    itemLongPress,
    containerShortPress,
    containerLongPress,
  }), [
    state.selectedIds,
    isSelectMode,
    isSelected,
    isExpanded,
    registerDisabled,
    clearSelection,
    setExpanded,
    itemShortPress,
    itemLongPress,
    containerShortPress,
    containerLongPress,
  ])

  return (
    <InteractionContext.Provider value={value}>
      {children}
    </InteractionContext.Provider>
  )
}

export function useInteraction() {
  const context = useContext(InteractionContext)
  if (!context) {
    throw new Error('useInteraction must be used within an InteractionProvider')
  }
  return context
}
