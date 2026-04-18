export const SummaryDataStatus = Object.freeze({
  UNKNOWN: 'unknown',
  LOADING: 'loading',
  AVAILABLE: 'available',
  ERROR: 'error',
})

export const SummaryDataEventType = Object.freeze({
  SUMMARY_REQUESTED: 'SUMMARY_REQUESTED',
  SUMMARY_LOAD_SUCCEEDED: 'SUMMARY_LOAD_SUCCEEDED',
  SUMMARY_LOAD_FAILED: 'SUMMARY_LOAD_FAILED',
  SUMMARY_RESET: 'SUMMARY_RESET',
  SUMMARY_ROLLBACK: 'SUMMARY_ROLLBACK',
})

export function getSummaryDataStatus(summaryData) {
  return summaryData?.status || SummaryDataStatus.UNKNOWN
}

/**
 * Reduces summary data state transitions for Domain B.
 * @example
 * reduceSummaryData(
 *   { status: 'unknown' },
 *   { type: SummaryDataEventType.SUMMARY_REQUESTED, effort: 'low' }
 * ).state
 * // => 'loading'
 */
export function reduceSummaryData(summaryData, event) {
  const currentStatus = getSummaryDataStatus(summaryData)

  switch (event.type) {
    case SummaryDataEventType.SUMMARY_REQUESTED:
      return {
        state: SummaryDataStatus.LOADING,
        patch: {
          status: SummaryDataStatus.LOADING,
          effort: event.effort,
          errorMessage: null,
        },
      }
    case SummaryDataEventType.SUMMARY_LOAD_SUCCEEDED:
      return {
        state: SummaryDataStatus.AVAILABLE,
        patch: {
          status: SummaryDataStatus.AVAILABLE,
          markdown: event.markdown,
          effort: event.effort,
          checkedAt: event.checkedAt,
          errorMessage: null,
        },
      }
    case SummaryDataEventType.SUMMARY_LOAD_FAILED:
      return {
        state: SummaryDataStatus.ERROR,
        patch: {
          status: SummaryDataStatus.ERROR,
          errorMessage: event.errorMessage,
        },
      }
    case SummaryDataEventType.SUMMARY_RESET:
      return {
        state: SummaryDataStatus.UNKNOWN,
        patch: {
          status: SummaryDataStatus.UNKNOWN,
          markdown: '',
          errorMessage: null,
          checkedAt: null,
        },
      }
    case SummaryDataEventType.SUMMARY_ROLLBACK:
      return {
        state: getSummaryDataStatus(event.previousData),
        patch: event.previousData || {
          status: SummaryDataStatus.UNKNOWN,
          markdown: '',
          errorMessage: null,
          checkedAt: null,
        },
      }
    default:
      return { state: currentStatus, patch: null }
  }
}
