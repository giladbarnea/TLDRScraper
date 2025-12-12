import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { useRef, useState } from 'react'
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

  const html = (() => {
    if (!markdown) return ''
    try {
      const rawHtml = marked.parse(markdown)
      return DOMPurify.sanitize(rawHtml)
    } catch (error) {
      console.error('Failed to parse markdown:', error)
      return ''
    }
  })()

  const errorMessage = data?.errorMessage || null
  const isAvailable = status === 'available' && markdown
  const isLoading = status === 'creating' || loading
  const isError = status === 'error'

  const buttonLabel = isLoading ? 'Loading...'
    : expanded ? 'Hide'
    : isAvailable ? 'Available'
    : isError ? 'Retry'
    : 'TLDR'

  const fetchTldr = async (summaryEffort = effort) => {
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
        return true
      } else {
        updateArticle((current) => ({
          [type]: {
            ...(current[type] || {}),
            status: 'error',
            errorMessage: result.error || `Failed to fetch ${type}`
          }
        }))
        return false
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
      return false
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false)
      }
    }
  }

  const toggle = async (summaryEffort) => {
    if (isAvailable) {
      setExpanded(!expanded)
      return isAvailable
    }
    return await fetchTldr(summaryEffort)
  }

  const collapse = () => {
    setExpanded(false)
  }

  const expand = () => {
    setExpanded(true)
  }

  const toggleVisibility = () => {
    if (isAvailable) {
      setExpanded(!expanded)
    }
  }

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
    fetch: fetchTldr,
    toggle,
    collapse,
    expand,
    toggleVisibility
  }
}
