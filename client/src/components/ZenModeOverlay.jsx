import { Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useOverlayContextMenu } from '../hooks/useOverlayContextMenu'
import BaseOverlay, { overlayProseClassName } from './BaseOverlay'
import ElaborationPreview from './ElaborationPreview'
import OverlayContextMenu from './OverlayContextMenu'

const IDLE_ELABORATION = Object.freeze({
  status: 'idle',
  selectedText: '',
  markdown: '',
  errorMessage: '',
})

function ZenModeOverlay({ url, html, summaryMarkdown, hostname, displayDomain, articleMeta, onClose, onMarkRemoved }) {
  const contextMenu = useOverlayContextMenu(true)
  const [elaboration, setElaboration] = useState(IDLE_ELABORATION)
  const abortControllerRef = useRef(null)

  const truncatedMeta = articleMeta && articleMeta.length > 22
    ? `${articleMeta.slice(0, 22)}...`
    : articleMeta

  useEffect(() => {
    return () => abortControllerRef.current?.abort()
  }, [])

  function closeElaboration() {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setElaboration(IDLE_ELABORATION)
  }

  async function runElaboration(selectedText) {
    abortControllerRef.current?.abort()
    const controller = new AbortController()
    abortControllerRef.current = controller

    setElaboration({ status: 'loading', selectedText, markdown: '', errorMessage: '' })

    try {
      const response = await window.fetch('/api/elaborate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          selected_text: selectedText,
          summary_markdown: summaryMarkdown,
        }),
        signal: controller.signal,
      })
      const result = await response.json()
      if (controller.signal.aborted) return

      if (!response.ok || !result.success) {
        setElaboration({
          status: 'error',
          selectedText,
          markdown: '',
          errorMessage: result.error || 'Failed to elaborate.',
        })
        return
      }

      setElaboration({
        status: 'available',
        selectedText,
        markdown: result.elaboration_markdown,
        errorMessage: '',
      })
    } catch (error) {
      if (error.name === 'AbortError') return
      setElaboration({
        status: 'error',
        selectedText,
        markdown: '',
        errorMessage: error.message || 'Failed to elaborate.',
      })
    }
  }

  const actions = [
    {
      key: 'elaborate',
      label: 'Elaborate',
      icon: <Sparkles size={15} />,
      onSelect: (selectedText) => {
        const trimmed = selectedText.trim()
        if (!trimmed) return
        runElaboration(trimmed)
      },
    },
  ]

  return (
    <>
      <BaseOverlay
        headerContent={(
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 hover:opacity-70 transition-opacity"
          >
            {hostname && (
              <img
                src={`https://www.google.com/s2/favicons?domain=${hostname}&sz=64`}
                className="w-4 h-4 rounded-full border border-slate-200"
                alt=""
              />
            )}
            <span className="text-sm text-slate-500 font-medium">
              {displayDomain}
              {truncatedMeta && <span className="text-slate-400"> · {truncatedMeta}</span>}
            </span>
          </a>
        )}
        onClose={onClose}
        onMarkRemoved={onMarkRemoved}
        onContentContextMenu={contextMenu.handleContextMenu}
      >
        <div className={overlayProseClassName} dangerouslySetInnerHTML={{ __html: html }} />
      </BaseOverlay>

      <OverlayContextMenu
        isOpen={contextMenu.isOpen}
        anchorX={contextMenu.anchorX}
        anchorY={contextMenu.anchorY}
        actions={actions}
        onClose={contextMenu.closeMenu}
        menuRef={contextMenu.menuRef}
      />

      <ElaborationPreview
        isOpen={elaboration.status !== 'idle'}
        status={elaboration.status}
        selectedText={elaboration.selectedText}
        markdown={elaboration.markdown}
        errorMessage={elaboration.errorMessage}
        onClose={closeElaboration}
      />
    </>
  )
}

export default ZenModeOverlay
