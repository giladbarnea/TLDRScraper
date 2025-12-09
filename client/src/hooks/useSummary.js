import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { useCallback, useMemo, useRef, useState } from 'react'
import { useArticleState } from './useArticleState'

export function useSummary(date, url, type = 'tldr') {
  if (type === 'summary') {
    throw new Error('Summary feature has been removed. Use type="tldr" instead.')
  }

  const { article, updateArticle } = useArticleState(date, url)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [effort, setEffort] = useState('low')
  const abortControllerRef = useRef(null)

  const data = article?.[type]
  const status = data?.status || 'unknown'
  const markdown = data?.markdown || ''

  const html = useMemo(() => {
    if (!markdown) return ''
    try {
      const rawHtml = marked.parse(markdown)
      return DOMPurify.sanitize(rawHtml)
    } catch (error) {
      console.error('Failed to parse markdown:', error)
      return ''
    }
  }, [markdown])

  const errorMessage = data?.errorMessage || null
  const isAvailable = status === 'available' && markdown
  const isLoading = status === 'creating' || loading
  const isError = status === 'error'

  const buttonLabel = useMemo(() => {
    if (isLoading) return 'Loading...'
    if (expanded) return 'Hide'
    if (isAvailable) return 'Available'
    if (isError) return 'Retry'
    return 'TLDR'
  }, [isLoading, expanded, isAvailable, isError])

  const fetch = useCallback(async (summaryEffort = effort) => {
    if (!article) return

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller

    setLoading(true)
    setEffort(summaryEffort)

    const endpoint = '/api/tldr-url'

    try {
      const response = await window.fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          summary_effort: summaryEffort
        }),
        signal: controller.signal
      })

      const result = await response.json()

      if (result.success) {
        updateArticle(() => ({
          [type]: {
            status: 'available',
            markdown: result[`${type}_markdown`] || '',
            effort: summaryEffort,
            checkedAt: new Date().toISOString(),
            errorMessage: null
          }
        }))
        setExpanded(true)
      } else {
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
  }, [article, url, type, effort, updateArticle])

  const toggle = useCallback((summaryEffort) => {
    if (isAvailable) {
      setExpanded(!expanded)
    } else {
      fetch(summaryEffort)
    }
  }, [isAvailable, expanded, fetch])

  const collapse = useCallback(() => {
    setExpanded(false)
  }, [])

  const expand = useCallback(() => {
    setExpanded(true)
  }, [])

  const toggleVisibility = useCallback(() => {
    if (isAvailable) {
      setExpanded(!expanded)
    }
  }, [isAvailable, expanded])

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
    buttonLabel,
    fetch,
    toggle,
    collapse,
    expand,
    toggleVisibility
  }
}
