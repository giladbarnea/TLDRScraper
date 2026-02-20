import DOMPurify from 'dompurify'
import { marked } from 'marked'
import markedKatex from 'marked-katex-extension'
import { useEffect, useRef, useState } from 'react'
import { logTransition, logTransitionSuccess } from '../lib/stateTransitionLogger'
import * as summaryDataReducer from '../reducers/summaryDataReducer'
import { useArticleState } from './useArticleState'
import { acquireZenOverlayLock, releaseZenOverlayLock } from './useZenOverlayLock'

marked.use(markedKatex({ throwOnError: false }))

export function useSummary(date, url, type = 'summary') {
  const { article, updateArticle, isRead, markAsRead } = useArticleState(date, url)
  const [expanded, setExpanded] = useState(false)
  const [effort, setEffort] = useState('low')
  const abortControllerRef = useRef(null)
  const requestTokenRef = useRef(null)
  const previousSummaryDataRef = useRef(null)

  const data = article?.[type] || null
  const status = summaryDataReducer.getSummaryDataStatus(data)
  const markdown = data?.markdown || ''

  const html = (() => {
    if (!markdown) return ''
    try {
      const rawHtml = marked.parse(markdown)
      return DOMPurify.sanitize(rawHtml, {
        ADD_TAGS: ['annotation', 'semantics']
      })
    } catch (error) {
      console.error('Failed to parse markdown:', error)
      return ''
    }
  })()

  const errorMessage = data?.errorMessage || null
  const isAvailable = status === summaryDataReducer.SummaryDataStatus.AVAILABLE && markdown
  const isLoading = status === summaryDataReducer.SummaryDataStatus.LOADING
  const isError = status === summaryDataReducer.SummaryDataStatus.ERROR

  const dispatchSummaryEvent = (event, extra = '') => {
    updateArticle((current) => {
      const currentData = current?.[type]
      const fromStatus = summaryDataReducer.getSummaryDataStatus(currentData)
      const { state: toStatus, patch } = summaryDataReducer.reduceSummaryData(currentData, event)

      if (fromStatus !== toStatus) {
        if (event.type === summaryDataReducer.SummaryDataEventType.SUMMARY_LOAD_SUCCEEDED) {
          logTransitionSuccess('summary-data', url, toStatus, extra)
        } else {
          logTransition('summary-data', url, fromStatus, toStatus, extra)
        }
      }

      if (!patch) return {}
      return {
        [type]: {
          ...(currentData || {}),
          ...patch,
        },
      }
    })
  }

  const createRequestToken = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`

  const fetchSummary = async (summaryEffort = effort) => {
    if (!article) return

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller

    const requestToken = createRequestToken()
    requestTokenRef.current = requestToken
    previousSummaryDataRef.current = data ? { ...data } : null

    setEffort(summaryEffort)
    dispatchSummaryEvent(
      {
        type: summaryDataReducer.SummaryDataEventType.SUMMARY_REQUESTED,
        effort: summaryEffort,
      },
      `effort=${summaryEffort}`
    )

    const endpoint = '/api/summarize-url'

    try {
      const response = await window.fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          summarize_effort: summaryEffort
        }),
        signal: controller.signal
      })

      const result = await response.json()

      if (requestTokenRef.current !== requestToken) return

      if (result.success) {
        dispatchSummaryEvent({
          type: summaryDataReducer.SummaryDataEventType.SUMMARY_LOAD_SUCCEEDED,
          markdown: result.summary_markdown,
          effort: summaryEffort,
          checkedAt: new Date().toISOString(),
        })
        requestTokenRef.current = null
        previousSummaryDataRef.current = null
        if (acquireZenOverlayLock(url)) {
          logTransition('summary-view', url, 'collapsed', 'expanded', 'summary-loaded')
          setExpanded(true)
        }
      } else {
        dispatchSummaryEvent(
          {
            type: summaryDataReducer.SummaryDataEventType.SUMMARY_LOAD_FAILED,
            errorMessage: result.error,
          },
          result.error
        )
        requestTokenRef.current = null
        previousSummaryDataRef.current = null
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        if (requestTokenRef.current === requestToken) {
          dispatchSummaryEvent({
            type: summaryDataReducer.SummaryDataEventType.SUMMARY_ROLLBACK,
            previousData: previousSummaryDataRef.current,
          })
          requestTokenRef.current = null
        }
        return
      }
      dispatchSummaryEvent(
        {
          type: summaryDataReducer.SummaryDataEventType.SUMMARY_LOAD_FAILED,
          errorMessage: error.message,
        },
        error.message
      )
      requestTokenRef.current = null
      previousSummaryDataRef.current = null
      console.error(`Failed to fetch ${type}:`, error)
    }
  }

  const toggle = (summaryEffort) => {
    if (isAvailable) {
      if (expanded) {
        collapse()
      } else if (acquireZenOverlayLock(url)) {
        logTransition('summary-view', url, 'collapsed', 'expanded', 'tap')
        setExpanded(true)
      }
    } else {
      fetchSummary(summaryEffort)
    }
  }

  const collapse = (markAsReadOnClose = true) => {
    logTransition('summary-view', url, 'expanded', 'collapsed')
    releaseZenOverlayLock(url)
    setExpanded(false)
    if (markAsReadOnClose && !isRead) markAsRead()
  }

  const expand = () => {
    if (acquireZenOverlayLock(url)) {
      logTransition('summary-view', url, 'collapsed', 'expanded', 'tap')
      setExpanded(true)
    }
  }

  useEffect(() => {
    return () => {
      releaseZenOverlayLock(url)
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [url])

  return {
    data,
    status,
    markdown,
    html,
    errorMessage,
    loading: isLoading,
    expanded,
    effort,
    isAvailable,
    isError,
    fetch: fetchSummary,
    toggle,
    collapse,
    expand
  }
}
