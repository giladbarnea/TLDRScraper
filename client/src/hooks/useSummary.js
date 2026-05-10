import { useEffect, useMemo } from 'react'
import { releaseZenLock } from '../lib/zenLock'
import * as summaryDataReducer from '../reducers/summaryDataReducer'
import { parseArticleKey, summaryActions, useArticleSlice } from '../store/articleStore'

export function useSummary(articleKey, type = 'summary') {
  const slice = useArticleSlice(articleKey)
  const { url } = parseArticleKey(articleKey)

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
    fetch: (summaryEffort) => summaryActions.fetch(articleKey, summaryEffort),
    toggle: (summaryEffort) => summaryActions.toggle(articleKey, summaryEffort),
    collapse: () => summaryActions.collapse(articleKey),
    expand: () => summaryActions.expand(articleKey),
  }), [articleKey])

  useEffect(() => {
    return () => {
      releaseZenLock(url)
      summaryActions.abort(articleKey)
    }
  }, [url, articleKey])

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
