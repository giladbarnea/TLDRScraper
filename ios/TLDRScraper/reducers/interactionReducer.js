export const InteractionEventType = Object.freeze({
  ITEM_SHORT_PRESS: 'ITEM_SHORT_PRESS',
  ITEM_LONG_PRESS: 'ITEM_LONG_PRESS',
  CONTAINER_SHORT_PRESS: 'CONTAINER_SHORT_PRESS',
  CONTAINER_LONG_PRESS: 'CONTAINER_LONG_PRESS',
  REGISTER_DISABLED: 'REGISTER_DISABLED',
  CLEAR_SELECTION: 'CLEAR_SELECTION',
  SET_EXPANDED: 'SET_EXPANDED',
})

export function createInitialInteractionState() {
  return {
    selectedIds: new Set(),
    disabledIds: new Set(),
    expandedContainerIds: new Set(),
    suppressNextShortPress: { id: null, untilMs: 0 },
  }
}

function cloneSet(set) {
  return new Set(set)
}

function nowMs() {
  return Date.now()
}

function latchSuppress(state, targetId, windowMs = 800) {
  return {
    ...state,
    suppressNextShortPress: {
      id: targetId,
      untilMs: nowMs() + windowMs,
    },
  }
}

export function shouldSuppressShortPress(state, targetId) {
  const latch = state.suppressNextShortPress
  if (!latch?.id) return false
  if (latch.id !== targetId) return false
  return nowMs() <= latch.untilMs
}

function clearSuppressLatch(state) {
  if (!state.suppressNextShortPress?.id) return state
  return { ...state, suppressNextShortPress: { id: null, untilMs: 0 } }
}

function toggleItemSelection(state, itemId) {
  if (state.disabledIds.has(itemId)) return state
  const nextSelected = cloneSet(state.selectedIds)
  if (nextSelected.has(itemId)) nextSelected.delete(itemId)
  else nextSelected.add(itemId)
  return { ...state, selectedIds: nextSelected }
}

function selectMany(state, itemIds) {
  const nextSelected = cloneSet(state.selectedIds)
  for (const id of itemIds) {
    if (!state.disabledIds.has(id)) nextSelected.add(id)
  }
  return { ...state, selectedIds: nextSelected }
}

function deselectMany(state, itemIds) {
  const nextSelected = cloneSet(state.selectedIds)
  for (const id of itemIds) nextSelected.delete(id)
  return { ...state, selectedIds: nextSelected }
}

function toggleContainerChildren(state, childIds) {
  const selectableChildIds = childIds.filter((id) => !state.disabledIds.has(id))
  if (selectableChildIds.length === 0) return state

  const allSelected = selectableChildIds.every((id) => state.selectedIds.has(id))
  return allSelected
    ? deselectMany(state, selectableChildIds)
    : selectMany(state, selectableChildIds)
}

function toggleExpand(state, containerId) {
  const nextExpanded = cloneSet(state.expandedContainerIds)
  if (nextExpanded.has(containerId)) nextExpanded.delete(containerId)
  else nextExpanded.add(containerId)
  return { ...state, expandedContainerIds: nextExpanded }
}

function setExpanded(state, containerId, expanded) {
  const nextExpanded = cloneSet(state.expandedContainerIds)
  if (expanded) nextExpanded.add(containerId)
  else nextExpanded.delete(containerId)
  return { ...state, expandedContainerIds: nextExpanded }
}

export function interactionReduce(state, event) {
  switch (event.type) {
    case InteractionEventType.REGISTER_DISABLED: {
      const { id, isDisabled } = event
      const nextDisabled = cloneSet(state.disabledIds)
      if (isDisabled) nextDisabled.add(id)
      else nextDisabled.delete(id)

      let nextState = { ...state, disabledIds: nextDisabled }

      if (isDisabled && nextState.selectedIds.has(id)) {
        const nextSelected = cloneSet(nextState.selectedIds)
        nextSelected.delete(id)
        nextState = { ...nextState, selectedIds: nextSelected }
      }

      return { state: nextState, decision: null }
    }

    case InteractionEventType.CLEAR_SELECTION: {
      const nextState = { ...state, selectedIds: new Set() }
      return { state: nextState, decision: null }
    }

    case InteractionEventType.SET_EXPANDED: {
      const { containerId, expanded } = event
      const nextState = setExpanded(state, containerId, expanded)
      return { state: nextState, decision: null }
    }

    case InteractionEventType.ITEM_LONG_PRESS: {
      const { itemId } = event
      let nextState = toggleItemSelection(state, itemId)
      nextState = latchSuppress(nextState, itemId)
      return { state: nextState, decision: null }
    }

    case InteractionEventType.CONTAINER_LONG_PRESS: {
      const { containerId, childIds } = event
      let nextState = toggleContainerChildren(state, childIds)
      nextState = latchSuppress(nextState, containerId)
      return { state: nextState, decision: null }
    }

    case InteractionEventType.CONTAINER_SHORT_PRESS: {
      const { containerId } = event
      if (shouldSuppressShortPress(state, containerId)) {
        const nextState = clearSuppressLatch(state)
        return { state: nextState, decision: null }
      }

      const nextState = toggleExpand(state, containerId)
      return { state: nextState, decision: null }
    }

    case InteractionEventType.ITEM_SHORT_PRESS: {
      const { itemId } = event
      if (shouldSuppressShortPress(state, itemId)) {
        const nextState = clearSuppressLatch(state)
        return { state: nextState, decision: null }
      }

      const inSelectMode = state.selectedIds.size > 0

      if (inSelectMode) {
        const nextState = toggleItemSelection(state, itemId)
        return { state: nextState, decision: null }
      }

      return { state, decision: { shouldOpenItem: true } }
    }

    default:
      return { state, decision: null }
  }
}
