import { BookOpen, Sparkles } from 'lucide-react'
import { useElaboration } from '../hooks/useElaboration'
import { useOverlayContextMenu } from '../hooks/useOverlayContextMenu'
import BaseOverlay, { overlayProseClassName } from './BaseOverlay'
import ElaborationPreview from './ElaborationPreview'

function DigestOverlay({ html, markdown, articleUrls, articleCount, errorMessage, onClose, onMarkRemoved }) {
  const contextMenu = useOverlayContextMenu(true)
  const { elaboration, runElaboration, closeElaboration } = useElaboration({
    sourceMarkdown: markdown,
    articleUrls,
  })

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
      overlayLayers={(
        <ElaborationPreview
          isOpen={elaboration.status !== 'idle'}
          status={elaboration.status}
          selectedText={elaboration.selectedText}
          markdown={elaboration.markdown}
          errorMessage={elaboration.errorMessage}
          onClose={closeElaboration}
        />
      )}
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
