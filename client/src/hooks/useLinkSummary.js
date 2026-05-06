import { useCallback, useEffect, useRef, useState } from 'react'

const IDLE_LINK_SUMMARY = Object.freeze({
  status: 'idle',
  selectedText: '',
  markdown: '',
  errorMessage: '',
})

export function useLinkSummary() {
  const [summary, setSummary] = useState(IDLE_LINK_SUMMARY)
  const abortControllerRef = useRef(null)

  useEffect(() => {
    return () => abortControllerRef.current?.abort()
  }, [])

  const closeSummary = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setSummary(IDLE_LINK_SUMMARY)
  }, [])

  const runSummary = useCallback(async ({ url, label }) => {
    abortControllerRef.current?.abort()
    const controller = new AbortController()
    abortControllerRef.current = controller

    const selectedText = label || url
    setSummary({ status: 'loading', selectedText, markdown: '', errorMessage: '' })

    try {
      const response = await window.fetch('/api/summarize-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
        signal: controller.signal,
      })
      const result = await response.json()
      if (controller.signal.aborted) return

      if (!response.ok || !result.success) {
        setSummary({
          status: 'error',
          selectedText,
          markdown: '',
          errorMessage: result.error || 'Failed to summarize link.',
        })
        return
      }

      setSummary({
        status: 'available',
        selectedText,
        markdown: result.summary_markdown,
        errorMessage: '',
      })
    } catch (error) {
      if (error.name === 'AbortError') return
      setSummary({
        status: 'error',
        selectedText,
        markdown: '',
        errorMessage: error.message || 'Failed to summarize link.',
      })
    }
  }, [])

  return { summary, runSummary, closeSummary }
}
