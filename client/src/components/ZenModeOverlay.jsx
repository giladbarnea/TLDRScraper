import { useMemo } from 'react'
import { useOverlayContextMenu } from '../hooks/useOverlayContextMenu'
import { useReadingOverlayMenuActions } from '../hooks/useReadingOverlayMenuActions'
import { markdownToHtml } from '../lib/markdownUtils'
import BaseOverlay, { overlayProseClassName } from './BaseOverlay'

function ZenModeOverlay({ url, summaryMarkdown, hostname, displayDomain, articleMeta, onClose, onMarkRemoved }) {
  const html = useMemo(() => markdownToHtml(summaryMarkdown), [summaryMarkdown])
  const contextMenu = useOverlayContextMenu(true)
  const { actions, overlayLayers } = useReadingOverlayMenuActions({
    sourceMarkdown: summaryMarkdown,
    articleUrls: [url],
  })

  const truncatedMeta = articleMeta && articleMeta.length > 22
    ? `${articleMeta.slice(0, 22)}...`
    : articleMeta

  const overlayMenu = {
    isOpen: contextMenu.isOpen,
    positionReference: contextMenu.positionReference,
    selectedText: contextMenu.selectedText,
    actionContext: contextMenu.actionContext,
    handleContextMenu: contextMenu.handleContextMenu,
    onOpenChange: contextMenu.onOpenChange,
    actions,
  }

  return (
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
      overlayMenu={overlayMenu}
      overlayLayers={overlayLayers}
    >
      <div className={overlayProseClassName} dangerouslySetInnerHTML={{ __html: html }} />
    </BaseOverlay>
  )
}

export default ZenModeOverlay
