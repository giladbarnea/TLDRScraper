const InteractionEventType = Object.freeze({
  ITEM_SHORT_PRESS: 'ITEM_SHORT_PRESS',
  ITEM_LONG_PRESS: 'ITEM_LONG_PRESS',
  CONTAINER_SHORT_PRESS: 'CONTAINER_SHORT_PRESS',
  CONTAINER_LONG_PRESS: 'CONTAINER_LONG_PRESS',
  CLEAR_SELECTION: 'CLEAR_SELECTION',
  SET_EXPANDED: 'SET_EXPANDED',
})

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

function shouldSuppressShortPress(state, targetId) {
  const latch = state.suppressNextShortPress
  if (!latch?.id) return false
  if (latch.id !== targetId) return false
  return nowMs() <= latch.untilMs
}

function clearSuppressLatch(state) {
  if (!state.suppressNextShortPress?.id) return state
  return { ...state, suppressNextShortPress: { id: null, untilMs: 0 } }
}

function defaultIsDisabled() {
  return false
}

function toggleItemSelection(state, itemId, isDisabled) {
  if (isDisabled(itemId)) return state
  const nextSelected = cloneSet(state.selectedIds)
  if (nextSelected.has(itemId)) nextSelected.delete(itemId)
  else nextSelected.add(itemId)
  return { ...state, selectedIds: nextSelected }
}

function selectMany(state, itemIds, isDisabled) {
  const nextSelected = cloneSet(state.selectedIds)
  for (const id of itemIds) {
    if (!isDisabled(id)) nextSelected.add(id)
  }
  return { ...state, selectedIds: nextSelected }
}

function deselectMany(state, itemIds) {
  const nextSelected = cloneSet(state.selectedIds)
  for (const id of itemIds) nextSelected.delete(id)
  return { ...state, selectedIds: nextSelected }
}

function toggleContainerChildren(state, childIds, isDisabled) {
  const selectableChildIds = childIds.filter((id) => !isDisabled(id))
  if (selectableChildIds.length === 0) return state

  const allSelected = selectableChildIds.every((id) => state.selectedIds.has(id))
  return allSelected
    ? deselectMany(state, selectableChildIds)
    : selectMany(state, selectableChildIds, isDisabled)
}

function toggleExpand(state, containerId) {
  const nextExpanded = cloneSet(state.expandedContainerIds)
  const nextUserCollapsed = cloneSet(state.userCollapsedContainerIds)
  if (nextExpanded.has(containerId)) {
    nextExpanded.delete(containerId)
    nextUserCollapsed.add(containerId)     // explicit collapse → protect from auto-expand
  } else {
    nextExpanded.add(containerId)
    nextUserCollapsed.delete(containerId)  // explicit (re)open → intent cleared
  }
  return { ...state, expandedContainerIds: nextExpanded, userCollapsedContainerIds: nextUserCollapsed }
}

function setExpanded(state, containerId, expanded) {
  const nextExpanded = cloneSet(state.expandedContainerIds)
  if (expanded) nextExpanded.add(containerId)
  else nextExpanded.delete(containerId)
  return { ...state, expandedContainerIds: nextExpanded }
}

export function interactionReduce(state, event, context = {}) {
  const isDisabled = context.isDisabled ?? defaultIsDisabled

  switch (event.type) {
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
      let nextState = toggleItemSelection(state, itemId, isDisabled)
      nextState = latchSuppress(nextState, itemId)
      return { state: nextState, decision: null }
    }

    case InteractionEventType.CONTAINER_LONG_PRESS: {
      const { containerId, childIds } = event
      let nextState = toggleContainerChildren(state, childIds, isDisabled)
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
        const nextState = toggleItemSelection(state, itemId, isDisabled)
        return { state: nextState, decision: null }
      }

      return { state, decision: { shouldOpenItem: true } }
    }

    default:
      return { state, decision: null }
  }
}
