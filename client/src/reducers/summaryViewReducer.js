export const SummaryViewMode = Object.freeze({
  COLLAPSED: 'collapsed',
  EXPANDED: 'expanded',
})

export const SummaryViewEventType = Object.freeze({
  OPEN_REQUESTED: 'OPEN_REQUESTED',
  CLOSE_REQUESTED: 'CLOSE_REQUESTED',
})

/**
 * @example
 * reduceSummaryView(
 *   { mode: SummaryViewMode.COLLAPSED, expandedBy: null },
 *   { type: SummaryViewEventType.OPEN_REQUESTED, reason: 'tap' }
 * ).state.mode
 * //=> 'expanded'
 */
export function reduceSummaryView(state, event) {
  switch (event.type) {
    case SummaryViewEventType.OPEN_REQUESTED:
      if (state.mode === SummaryViewMode.EXPANDED) {
        return { state }
      }
      return {
        state: {
          mode: SummaryViewMode.EXPANDED,
          expandedBy: event.reason || null,
        },
      }
    case SummaryViewEventType.CLOSE_REQUESTED:
      if (state.mode === SummaryViewMode.COLLAPSED) {
        return { state }
      }
      return {
        state: {
          mode: SummaryViewMode.COLLAPSED,
          expandedBy: null,
        },
      }
    default:
      return { state }
  }
}
