import { useCallback, useEffect, useRef, useState } from 'react'

const IDLE_URL_SUMMARY = Object.freeze({
  status: 'idle',
  selectedText: '',
  markdown: '',
  errorMessage: '',
})

export function useUrlSummary() {
  const [urlSummary, setUrlSummary] = useState(IDLE_URL_SUMMARY)
  const abortControllerRef = useRef(null)

  useEffect(() => {
    return () => abortControllerRef.current?.abort()
  }, [])

  const closeUrlSummary = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setUrlSummary(IDLE_URL_SUMMARY)
  }, [])

  const runUrlSummary = useCallback(async ({ url, label }) => {
    abortControllerRef.current?.abort()
    const controller = new AbortController()
    abortControllerRef.current = controller

    setUrlSummary({ status: 'loading', selectedText: label || url, markdown: '', errorMessage: '' })

    try {
      const response = await window.fetch('/api/summarize-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, summarize_effort: 'low' }),
        signal: controller.signal,
      })
      const result = await response.json()
      if (controller.signal.aborted) return

      if (!response.ok || !result.success) {
        setUrlSummary({
          status: 'error',
          selectedText: label || url,
          markdown: '',
          errorMessage: result.error || 'Failed to summarize.',
        })
        return
      }

      setUrlSummary({
        status: 'available',
        selectedText: label || result.canonical_url || url,
        markdown: result.summary_markdown,
        errorMessage: '',
      })
    } catch (error) {
      if (error.name === 'AbortError') return
      setUrlSummary({
        status: 'error',
        selectedText: label || url,
        markdown: '',
        errorMessage: error.message || 'Failed to summarize.',
      })
    }
  }, [])

  return { urlSummary, runUrlSummary, closeUrlSummary }
}
