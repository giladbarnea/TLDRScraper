import { BookOpen } from 'lucide-react'
import { useMemo } from 'react'
import { useOverlayContextMenu } from '../hooks/useOverlayContextMenu'
import { useReadingOverlayMenuActions } from '../hooks/useReadingOverlayMenuActions'
import { markdownToHtml } from '../lib/markdownUtils'
import BaseOverlay, { overlayProseClassName } from './BaseOverlay'

function DigestOverlay({ markdown, articleUrls, articleCount, errorMessage, onClose, onMarkRemoved }) {
  const html = useMemo(() => markdownToHtml(markdown), [markdown])
  const contextMenu = useOverlayContextMenu(true)
  const { actions, overlayLayers } = useReadingOverlayMenuActions({
    sourceMarkdown: markdown,
    articleUrls,
  })

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
        <div className="flex items-center gap-2">
          <BookOpen size={16} className="text-slate-500" />
          <span className="text-sm text-slate-500 font-medium">
            {articleCount} {articleCount === 1 ? 'article' : 'articles'}
          </span>
        </div>
      )}
      onClose={onClose}
      onMarkRemoved={onMarkRemoved}
      overlayMenu={overlayMenu}
      overlayLayers={overlayLayers}
    >
      {errorMessage && !html ? (
        <div className="text-sm text-red-500 bg-red-50 p-4 rounded-lg">{errorMessage}</div>
      ) : (
        <div className={overlayProseClassName} dangerouslySetInnerHTML={{ __html: html }} />
      )}
    </BaseOverlay>
  )
}

export default DigestOverlay
