import { ExternalLink, FileText, Sparkles } from 'lucide-react'
import { useMemo } from 'react'
import ElaborationPreview from '../components/ElaborationPreview'
import { useElaboration } from './useElaboration'
import { useLinkSummary } from './useLinkSummary'

function isTextSelectionContext(actionContext) {
  return actionContext?.kind !== 'link'
}

function isLinkContext(actionContext) {
  return actionContext?.kind === 'link'
}

function openLink(_text, actionContext) {
  window.open(actionContext.url, '_blank', 'noopener,noreferrer')
}

export function useReadingOverlayMenuActions({ sourceMarkdown, articleUrls }) {
  const { elaboration, runElaboration, closeElaboration } = useElaboration({
    sourceMarkdown,
    articleUrls,
  })
  const { summary: linkSummary, runSummary: runLinkSummary, closeSummary: closeLinkSummary } = useLinkSummary()

  const actions = useMemo(() => [
    {
      key: 'elaborate',
      label: 'Elaborate',
      icon: <Sparkles size={15} />,
      isVisible: isTextSelectionContext,
      onSelect: runElaboration,
    },
    {
      key: 'open-link',
      label: 'Open',
      icon: <ExternalLink size={15} />,
      isVisible: isLinkContext,
      onSelect: openLink,
    },
    {
      key: 'summarize-link',
      label: 'Summarize',
      icon: <FileText size={15} />,
      isVisible: isLinkContext,
      onSelect: (_text, actionContext) => runLinkSummary(actionContext),
    },
  ], [runElaboration, runLinkSummary])

  const overlayLayers = (
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
        isOpen={linkSummary.status !== 'idle'}
        status={linkSummary.status}
        selectedText={linkSummary.selectedText}
        markdown={linkSummary.markdown}
        errorMessage={linkSummary.errorMessage}
        onClose={closeLinkSummary}
        ariaLabel="Link summary"
        loadingLabel="Summarizing…"
        errorFallback="Link summary failed. Try again."
      />
    </>
  )

  return { actions, overlayLayers }
}
