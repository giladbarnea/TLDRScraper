import { ExternalLink, FileText, Sparkles } from 'lucide-react'
import { useMemo } from 'react'
import { useElaboration } from '../hooks/useElaboration'
import { useOverlayContextMenu } from '../hooks/useOverlayContextMenu'
import { useUrlSummary } from '../hooks/useUrlSummary'
import { markdownToHtml } from '../lib/markdownUtils'
import BaseOverlay, { overlayProseClassName } from './BaseOverlay'
import ElaborationPreview from './ElaborationPreview'

function ZenModeOverlay({ url, summaryMarkdown, hostname, displayDomain, articleMeta, onClose, onMarkRemoved }) {
  const html = useMemo(() => markdownToHtml(summaryMarkdown), [summaryMarkdown])
  const contextMenu = useOverlayContextMenu(true)
  const { elaboration, runElaboration, closeElaboration } = useElaboration({
    sourceMarkdown: summaryMarkdown,
    articleUrls: [url],
  })
  const { urlSummary, runUrlSummary, closeUrlSummary } = useUrlSummary()

  const truncatedMeta = articleMeta && articleMeta.length > 22
    ? `${articleMeta.slice(0, 22)}...`
    : articleMeta

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
      <div className={overlayProseClassName} dangerouslySetInnerHTML={{ __html: html }} />
    </BaseOverlay>
  )
}

export default ZenModeOverlay
