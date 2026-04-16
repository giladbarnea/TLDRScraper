import { BookOpen, Check, ChevronDown } from 'lucide-react'
import { useOverlayContextMenu } from '../hooks/useOverlayContextMenu'
import BaseOverlay, { overlayProseClassName } from './BaseOverlay'
import OverlayContextMenu from './OverlayContextMenu'

function DigestOverlay({ html, expanded, articleCount, errorMessage, onClose, onMarkRemoved }) {
  const contextMenu = useOverlayContextMenu(expanded)

  const actions = [
    { label: 'Close reader', icon: <ChevronDown size={14} />, onSelect: onClose },
    { label: 'Mark done', icon: <Check size={14} />, onSelect: onMarkRemoved },
  ]

  return (
    <>
      <BaseOverlay
        expanded={expanded}
        headerContent={(
          <div className="flex items-center gap-2">
            <BookOpen size={16} className="text-slate-500" />
            <span className="text-sm text-slate-500 font-medium">
              {articleCount} {articleCount === 1 ? 'article' : 'articles'}
            </span>
          </div>
        )}
        onClose={onClose}
        onMarkRemoved={onMarkRemoved}
        onContentContextMenu={contextMenu.handleContextMenu}
      >
        {errorMessage && !html ? (
          <div className="text-sm text-red-500 bg-red-50 p-4 rounded-lg">{errorMessage}</div>
        ) : (
          <div className={overlayProseClassName} dangerouslySetInnerHTML={{ __html: html }} />
        )}
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

export default DigestOverlay
