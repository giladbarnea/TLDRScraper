import { useCallback, useEffect, useRef, useState } from 'react'

const IDLE_ELABORATION = Object.freeze({
  status: 'idle',
  selectedText: '',
  markdown: '',
  errorMessage: '',
})

export function useElaboration({ sourceMarkdown, articleUrls }) {
  const [elaboration, setElaboration] = useState(IDLE_ELABORATION)
  const abortControllerRef = useRef(null)

  useEffect(() => {
    return () => abortControllerRef.current?.abort()
  }, [])

  const closeElaboration = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setElaboration(IDLE_ELABORATION)
  }, [])

  const runElaboration = useCallback(async (selectedText) => {
    const trimmed = selectedText.trim()
    console.log('[elaborate] onSelect — raw:', JSON.stringify(selectedText.slice(0, 40)), '| trimmed:', JSON.stringify(trimmed.slice(0, 40)))
    if (!trimmed) return

    abortControllerRef.current?.abort()
    const controller = new AbortController()
    abortControllerRef.current = controller

    console.log('[elaborate] starting — text:', trimmed.slice(0, 60))
    setElaboration({ status: 'loading', selectedText: trimmed, markdown: '', errorMessage: '' })

    try {
      console.log('[elaborate] sending POST /api/elaborate — articleUrls:', articleUrls?.length)
      const response = await window.fetch('/api/elaborate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          selected_text: trimmed,
          source_markdown: sourceMarkdown,
          article_urls: articleUrls,
        }),
        signal: controller.signal,
      })
      console.log('[elaborate] response received — status:', response.status, '| aborted:', controller.signal.aborted)
      const result = await response.json()
      if (controller.signal.aborted) {
        console.log('[elaborate] aborted after response — discarding')
        return
      }

      if (!response.ok || !result.success) {
        console.log('[elaborate] error response —', result.error)
        setElaboration({
          status: 'error',
          selectedText: trimmed,
          markdown: '',
          errorMessage: result.error || 'Failed to elaborate.',
        })
        return
      }

      console.log('[elaborate] success — markdown length:', result.elaboration_markdown?.length)
      setElaboration({
        status: 'available',
        selectedText: trimmed,
        markdown: result.elaboration_markdown,
        errorMessage: '',
      })
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('[elaborate] fetch aborted')
        return
      }
      console.log('[elaborate] fetch error —', error.message)
      setElaboration({
        status: 'error',
        selectedText: trimmed,
        markdown: '',
        errorMessage: error.message || 'Failed to elaborate.',
      })
    }
  }, [sourceMarkdown, articleUrls])

  return { elaboration, runElaboration, closeElaboration }
}
