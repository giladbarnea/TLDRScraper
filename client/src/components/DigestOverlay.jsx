import { BookOpen, ExternalLink, FileText, Sparkles } from 'lucide-react'
import { useMemo } from 'react'
import { useElaboration } from '../hooks/useElaboration'
import { useOverlayContextMenu } from '../hooks/useOverlayContextMenu'
import { useUrlSummary } from '../hooks/useUrlSummary'
import { markdownToHtml } from '../lib/markdownUtils'
import BaseOverlay, { overlayProseClassName } from './BaseOverlay'
import ElaborationPreview from './ElaborationPreview'

function DigestOverlay({ markdown, articleUrls, articleCount, errorMessage, onClose, onMarkRemoved }) {
  const html = useMemo(() => markdownToHtml(markdown), [markdown])
  const contextMenu = useOverlayContextMenu(true)
  const { elaboration, runElaboration, closeElaboration } = useElaboration({
    sourceMarkdown: markdown,
    articleUrls,
  })
  const { urlSummary, runUrlSummary, closeUrlSummary } = useUrlSummary()

  const openContextLink = ({ url }) => {
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  const selectionActions = [
    {
      key: 'elaborate',
      label: 'Elaborate',
      icon: <Sparkles size={15} />,
      onSelect: runElaboration,
    },
  ]

  const linkActions = [
    {
      key: 'open-link',
      label: 'Open',
      icon: <ExternalLink size={15} />,
      getPayload: ({ linkUrl }) => ({ url: linkUrl }),
      onSelect: openContextLink,
    },
    {
      key: 'summarize-link',
      label: 'Summarize',
      icon: <FileText size={15} />,
      getPayload: ({ linkUrl, linkText }) => ({ url: linkUrl, label: linkText }),
      onSelect: runUrlSummary,
    },
  ]

  const actions = contextMenu.linkUrl ? linkActions : selectionActions

  const overlayMenu = {
    isOpen: contextMenu.isOpen,
    positionReference: contextMenu.positionReference,
    selectedText: contextMenu.selectedText,
    linkUrl: contextMenu.linkUrl,
    linkText: contextMenu.linkText,
    handleContextMenu: contextMenu.handleContextMenu,
    linkLongPressHandlers: contextMenu.linkLongPressHandlers,
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
        <>
          <ElaborationPreview
            isOpen={elaboration.status !== 'idle'}
            status={elaboration.status}
            selectedText={elaboration.selectedText}
            markdown={elaboration.markdown}
            errorMessage={elaboration.errorMessage}
            onClose={closeElaboration}
          />
          <ElaborationPreview
            isOpen={urlSummary.status !== 'idle'}
            status={urlSummary.status}
            selectedText={urlSummary.selectedText}
            markdown={urlSummary.markdown}
            errorMessage={urlSummary.errorMessage}
            onClose={closeUrlSummary}
            ariaLabel="Link summary"
            loadingMessage="Summarizing…"
            errorDefaultMessage="Summary failed. Try again."
          />
        </>
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
