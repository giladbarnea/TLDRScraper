export const SummaryDataStatus = Object.freeze({
  UNKNOWN: 'unknown',
  LOADING: 'loading',
  AVAILABLE: 'available',
  ERROR: 'error',
})

const MAX_LOADING_STATE_AGE_MILLISECONDS = 2 * 60 * 1000

export const SummaryDataEventType = Object.freeze({
  SUMMARY_REQUESTED: 'SUMMARY_REQUESTED',
  SUMMARY_LOAD_SUCCEEDED: 'SUMMARY_LOAD_SUCCEEDED',
  SUMMARY_LOAD_FAILED: 'SUMMARY_LOAD_FAILED',
  SUMMARY_RESET: 'SUMMARY_RESET',
  SUMMARY_ROLLBACK: 'SUMMARY_ROLLBACK',
})

export function getSummaryDataStatus(summaryData) {
  const status = summaryData?.status || SummaryDataStatus.UNKNOWN
  if (status !== SummaryDataStatus.LOADING) {
    return status
  }

  const requestedAtIso = summaryData?.requestedAt
  if (!requestedAtIso) {
    return SummaryDataStatus.UNKNOWN
  }

  const requestedAtUnixMilliseconds = Date.parse(requestedAtIso)
  if (Number.isNaN(requestedAtUnixMilliseconds)) {
    return SummaryDataStatus.UNKNOWN
  }

  const loadingDurationMilliseconds = Date.now() - requestedAtUnixMilliseconds
  if (loadingDurationMilliseconds > MAX_LOADING_STATE_AGE_MILLISECONDS) {
    return SummaryDataStatus.UNKNOWN
  }

  return SummaryDataStatus.LOADING
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
          requestedAt: event.requestedAt,
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
          requestedAt: null,
          errorMessage: null,
        },
      }
    case SummaryDataEventType.SUMMARY_LOAD_FAILED:
      return {
        state: SummaryDataStatus.ERROR,
        patch: {
          status: SummaryDataStatus.ERROR,
          requestedAt: null,
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
          requestedAt: null,
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
          requestedAt: null,
          checkedAt: null,
        },
      }
    default:
      return { state: currentStatus, patch: null }
  }
}
