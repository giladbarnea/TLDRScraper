import { Sparkles } from 'lucide-react'
import { useElaboration } from '../hooks/useElaboration'
import { useOverlayContextMenu } from '../hooks/useOverlayContextMenu'
import BaseOverlay, { overlayProseClassName } from './BaseOverlay'
import ElaborationPreview from './ElaborationPreview'

function ZenModeOverlay({ url, html, summaryMarkdown, hostname, displayDomain, articleMeta, onClose, onMarkRemoved }) {
  const contextMenu = useOverlayContextMenu(true)
  const { elaboration, runElaboration, closeElaboration } = useElaboration({
    sourceMarkdown: summaryMarkdown,
    articleUrls: [url],
  })

  const truncatedMeta = articleMeta && articleMeta.length > 22
    ? `${articleMeta.slice(0, 22)}...`
    : articleMeta

  const actions = [
    {
      key: 'elaborate',
      label: 'Elaborate',
      icon: <Sparkles size={15} />,
      onSelect: runElaboration,
    },
  ]

  const overlayMenu = {
    isOpen: contextMenu.isOpen,
    positionReference: contextMenu.positionReference,
    selectedText: contextMenu.selectedText,
    menuRef: contextMenu.menuRef,
    handleContextMenu: contextMenu.handleContextMenu,
    closeMenu: contextMenu.closeMenu,
    actions,
  }

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
        overlayMenu={overlayMenu}
      >
        <div className={overlayProseClassName} dangerouslySetInnerHTML={{ __html: html }} />
      </BaseOverlay>

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
