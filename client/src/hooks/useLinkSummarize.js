import { useCallback, useEffect, useRef, useState } from 'react'

const IDLE_LINK_SUMMARY = Object.freeze({
  status: 'idle',
  url: '',
  markdown: '',
  errorMessage: '',
})

export function useLinkSummarize() {
  const [linkSummary, setLinkSummary] = useState(IDLE_LINK_SUMMARY)
  const abortControllerRef = useRef(null)

  useEffect(() => {
    return () => abortControllerRef.current?.abort()
  }, [])

  const closeLinkSummary = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setLinkSummary(IDLE_LINK_SUMMARY)
  }, [])

  const runLinkSummarize = useCallback(async (url) => {
    if (!url) return

    abortControllerRef.current?.abort()
    const controller = new AbortController()
    abortControllerRef.current = controller

    console.log('[link-summarize] starting — url:', url.slice(0, 80))
    setLinkSummary({ status: 'loading', url, markdown: '', errorMessage: '' })

    try {
      const response = await window.fetch('/api/summarize-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
        signal: controller.signal,
      })
      const result = await response.json()
      if (controller.signal.aborted) {
        console.log('[link-summarize] aborted after response — discarding')
        return
      }

      if (!response.ok || !result.success) {
        console.log('[link-summarize] error response —', result.error)
        setLinkSummary({ status: 'error', url, markdown: '', errorMessage: result.error || 'Failed to summarize.' })
        return
      }

      console.log('[link-summarize] success — markdown length:', result.summary_markdown?.length)
      setLinkSummary({ status: 'available', url, markdown: result.summary_markdown, errorMessage: '' })
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('[link-summarize] fetch aborted')
        return
      }
      console.log('[link-summarize] fetch error —', error.message)
      setLinkSummary({ status: 'error', url, markdown: '', errorMessage: error.message || 'Failed to summarize.' })
    }
  }, [])

  return { linkSummary, runLinkSummarize, closeLinkSummary }
}
