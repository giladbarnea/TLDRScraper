import DOMPurify from 'dompurify'
import { marked } from 'marked'
import markedKatex from 'marked-katex-extension'
import { useEffect, useRef, useState } from 'react'
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

export function useSummary(date, url, type = 'tldr') {
  if (type === 'summary') {
    throw new Error('Summary feature has been removed. Use type="tldr" instead.')
  }

  const { article, updateArticle, isRead, markAsRead } = useArticleState(date, url)
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
  const isLoading = status === 'creating' || loading
  const isError = status === 'error'

  const fetchTldr = async (tldrEffort = effort) => {
    if (!article) return

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller

    setLoading(true)
    setEffort(tldrEffort)

    const endpoint = '/api/tldr-url'

    try {
      const response = await window.fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          tldr_effort: tldrEffort
        }),
        signal: controller.signal
      })

      const result = await response.json()

      if (result.success) {
        updateArticle(() => ({
          [type]: {
            status: 'available',
            markdown: result[`${type}_markdown`] || '',
            effort: tldrEffort,
            checkedAt: new Date().toISOString(),
            errorMessage: null
          }
        }))
        if (acquireZenLock(url)) {
          setExpanded(true)
        }
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
      // Only reset loading if this fetch wasn't aborted. In practice, abort only happens
      // when a NEW fetch starts (line 56-57), so a successor fetch always completes and resets loading.
      if (!controller.signal.aborted) {
        setLoading(false)
      }
    }
  }

  const toggle = (tldrEffort) => {
    if (isAvailable) {
      if (expanded) {
        collapse()
      } else if (acquireZenLock(url)) {
        setExpanded(true)
      }
    } else {
      fetchTldr(tldrEffort)
    }
  }

  const collapse = () => {
    releaseZenLock(url)
    setExpanded(false)
    if (!isRead) markAsRead()
  }

  const expand = () => {
    if (acquireZenLock(url)) {
      setExpanded(true)
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
    expanded,
    effort,
    isAvailable,
    isError,
    fetch: fetchTldr,
    toggle,
    collapse,
    expand
  }
}
