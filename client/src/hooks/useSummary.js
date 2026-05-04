import { useEffect, useMemo } from 'react'
import { releaseZenLock } from '../lib/zenLock'
import * as summaryDataReducer from '../reducers/summaryDataReducer'
import { summaryActions, useArticleSlice } from '../store/articleStore'

export function useSummary(date, url, type = 'summary') {
  const slice = useArticleSlice(date, url)
  const key = `${date}::${url}`

  const data = slice?.[type] || null
  const status = summaryDataReducer.getSummaryDataStatus(data)
  const markdown = data?.markdown || ''
  const errorMessage = data?.errorMessage || null
  const isAvailable = status === summaryDataReducer.SummaryDataStatus.AVAILABLE && markdown
  const isLoading = status === summaryDataReducer.SummaryDataStatus.LOADING
  const isError = status === summaryDataReducer.SummaryDataStatus.ERROR
  const expanded = slice?.expandedView ?? false
  const effort = data?.effort || 'low'

  const commands = useMemo(() => Object.freeze({
    fetch: (summaryEffort) => summaryActions.fetch(key, summaryEffort),
    toggle: (summaryEffort) => summaryActions.toggle(key, summaryEffort),
    collapse: () => summaryActions.collapse(key),
    expand: () => summaryActions.expand(key),
  }), [key])

  useEffect(() => {
    return () => {
      releaseZenLock(url)
      summaryActions.abort(key)
    }
  }, [url, key])

  return useMemo(() => ({
    data,
    status,
    markdown,
    errorMessage,
    loading: isLoading,
    expanded,
    effort,
    isAvailable,
    isError,
    ...commands,
  }), [data, status, markdown, errorMessage, isLoading, expanded, effort, isAvailable, isError, commands])
}
