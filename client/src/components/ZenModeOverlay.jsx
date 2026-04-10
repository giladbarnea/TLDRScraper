import { Check, ChevronDown } from 'lucide-react'
import { useOverlayContextMenu } from '../hooks/useOverlayContextMenu'
import BaseOverlay, { overlayProseClassName } from './BaseOverlay'
import OverlayContextMenu from './OverlayContextMenu'

function ZenModeOverlay({ url, html, hostname, displayDomain, articleMeta, onClose, onMarkRemoved }) {
  const contextMenu = useOverlayContextMenu()
  const truncatedMeta = articleMeta && articleMeta.length > 22
    ? `${articleMeta.slice(0, 22)}...`
    : articleMeta
  const actions = [
    {
      key: 'close-reader',
      label: 'Close reader',
      icon: <ChevronDown size={15} />,
      onSelect: onClose,
    },
    {
      key: 'mark-done',
      label: 'Mark done',
      icon: <Check size={15} />,
      onSelect: onMarkRemoved,
      tone: 'success',
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
    </>
  )
}

export default ZenModeOverlay
