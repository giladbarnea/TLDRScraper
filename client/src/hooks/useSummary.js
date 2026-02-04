import DOMPurify from 'dompurify'
import { marked } from 'marked'
import markedKatex from 'marked-katex-extension'
import { useEffect, useRef, useState } from 'react'
import { logTransition, logTransitionSuccess } from '../lib/stateTransitionLogger'
import {
  SummaryViewEventType,
  SummaryViewMode,
  reduceSummaryView,
} from '../reducers/summaryViewReducer'
import { useArticleState } from './useArticleState'

marked.use(markedKatex({ throwOnError: false }))

let zenLockOwner = null

function acquireZenLock(url) {
  if (zenLockOwner === null) {
    zenLockOwner = url
    return true
  }
  return false
}

function releaseZenLock(url) {
  if (zenLockOwner === url) {
    zenLockOwner = null
  }
}

export function useSummary(date, url, type = 'summary') {
  const { article, updateArticle, isRead, markAsRead } = useArticleState(date, url)
  const [loading, setLoading] = useState(false)
  const [summaryViewState, setSummaryViewState] = useState({
    mode: SummaryViewMode.COLLAPSED,
    expandedBy: null,
  })
  const [effort, setEffort] = useState('low')
  const abortControllerRef = useRef(null)

  const data = article?.[type]
  const status = data?.status || 'unknown'
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
  const isAvailable = status === 'available' && markdown
  const isLoading = status === 'loading' || loading
  const isError = status === 'error'
  const isExpanded = summaryViewState.mode === SummaryViewMode.EXPANDED

  const dispatchSummaryViewEvent = (event) => {
    setSummaryViewState((current) => {
      const { state: next } = reduceSummaryView(current, event)
      if (current.mode !== next.mode) {
        logTransition('summary-view', url, current.mode, next.mode)
      }
      return next
    })
  }

  const fetchSummary = async (summaryEffort = effort) => {
    if (!article) return

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller

    logTransition('summary-data', url, status, 'loading', `effort=${summaryEffort}`)
    setLoading(true)
    setEffort(summaryEffort)

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

      if (result.success) {
        logTransitionSuccess('summary-data', url, 'available')
        updateArticle(() => ({
          [type]: {
            status: 'available',
            markdown: result.summary_markdown || '',
            effort: summaryEffort,
            checkedAt: new Date().toISOString(),
            errorMessage: null
          }
        }))
        if (acquireZenLock(url)) {
          dispatchSummaryViewEvent({
            type: SummaryViewEventType.OPEN_REQUESTED,
            reason: 'summary-loaded',
          })
        }
      } else {
        logTransition('summary-data', url, 'loading', 'error', result.error)
        updateArticle((current) => ({
          [type]: {
            ...(current[type] || {}),
            status: 'error',
            errorMessage: result.error || `Failed to fetch ${type}`
          }
        }))
      }
    } catch (error) {
      if (error.name === 'AbortError') return
      logTransition('summary-data', url, 'loading', 'error', error.message)
      updateArticle((current) => ({
        [type]: {
          ...(current[type] || {}),
          status: 'error',
          errorMessage: error.message || 'Network error'
        }
      }))
      console.error(`Failed to fetch ${type}:`, error)
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false)
      }
    }
  }

  const toggle = (summaryEffort) => {
    if (isAvailable) {
      if (isExpanded) {
        collapse()
      } else if (acquireZenLock(url)) {
        dispatchSummaryViewEvent({
          type: SummaryViewEventType.OPEN_REQUESTED,
          reason: 'tap',
        })
      }
    } else {
      fetchSummary(summaryEffort)
    }
  }

  const collapse = (markAsReadOnClose = true) => {
    releaseZenLock(url)
    dispatchSummaryViewEvent({ type: SummaryViewEventType.CLOSE_REQUESTED })
    if (markAsReadOnClose && !isRead) markAsRead()
  }

  const expand = () => {
    if (acquireZenLock(url)) {
      dispatchSummaryViewEvent({
        type: SummaryViewEventType.OPEN_REQUESTED,
        reason: 'tap',
      })
    }
  }

  useEffect(() => {
    return () => {
      releaseZenLock(url)
    }
  }, [url])

  return {
    data,
    status,
    markdown,
    html,
    errorMessage,
    loading: isLoading,
    expanded: isExpanded,
    effort,
    isAvailable,
    isError,
    fetch: fetchSummary,
    toggle,
    collapse,
    expand
  }
}
