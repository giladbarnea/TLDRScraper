import { motion } from 'framer-motion'
import { AlertCircle, CheckCircle, Trash2, Undo2 } from 'lucide-react'
import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useArticleState } from '../hooks/useArticleState'
import { useSummary } from '../hooks/useSummary'
import { useSwipeToRemove } from '../hooks/useSwipeToRemove'
import { getFaviconUrl } from '../lib/faviconUrl'
import { interactionActions, useArticleSlice, useIsSelectMode } from '../store/articleStore'
import Selectable from './Selectable'
import ZenModeOverlay from './ZenModeOverlay'

function ErrorToast({ message, onDismiss }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000)
    return () => clearTimeout(timer)
  }, [onDismiss])

  return createPortal(
    <div className="fixed bottom-4 left-4 right-4 z-[200] bg-red-600 text-white p-4 rounded-lg shadow-elevated flex items-start gap-3">
      <AlertCircle size={20} className="shrink-0 mt-0.5" />
      <div className="flex-1 text-sm font-medium break-all">{message}</div>
      <button onClick={onDismiss} className="shrink-0 text-white/80 hover:text-white">✕</button>
    </div>,
    document.body
  )
}

function ArticleTitle({ isRead, title }) {
  return (
    <span
      className={`
        text-[15px] font-display font-medium leading-snug text-slate-900
        block tracking-tight
        ${isRead ? 'text-slate-400 font-normal' : ''}
      `}
    >
      {title}
    </span>
  )
}

function ArticleMeta({ hostname, domain, articleMeta }) {
  const faviconUrl = getFaviconUrl(hostname)

  return (
    <div className="flex items-center gap-2 min-w-0">
      {faviconUrl && (
        <div className="w-4 h-4 rounded-full bg-white border border-slate-200 overflow-hidden flex items-center justify-center shrink-0">
          <img
            src={faviconUrl}
            alt={domain}
            className="w-full h-full object-contain"
            loading="lazy"
            decoding="async"
            onError={(event) => { event.currentTarget.style.visibility = 'hidden' }}
          />
        </div>
      )}
      <div className="flex items-baseline gap-1.5 text-xs leading-none min-w-0">
        <span className="font-medium text-slate-400 shrink-0">
          {domain && domain}
        </span>
        <span className="text-slate-300 shrink-0">·</span>
        <span className="font-normal text-slate-400 truncate">
          {articleMeta}
        </span>
      </div>
    </div>
  )
}

function SummaryError({ message }) {
  return (
    <div className="mt-4 text-xs text-red-500 bg-red-50 p-3 rounded-lg">
      {message || 'Failed to load summary.'}
    </div>
  )
}

function ArticleCard({ articleKey }) {
  const slice = useArticleSlice(articleKey)
  const isSelectMode = useIsSelectMode()
  const { isRead, isRemoved, toggleRemove, markAsRead, markAsRemoved, loading: stateLoading } = useArticleState(articleKey)
  const summary = useSummary(articleKey)
  const { isAvailable } = summary

  const componentId = articleKey

  const handleSummaryClose = (markAsReadOnClose = true) => {
    summary.collapse()
    if (markAsReadOnClose && !isRead) markAsRead()
  }

  const handleSwipeComplete = () => {
    if (!isRemoved && summary.expanded) handleSummaryClose()
    toggleRemove()
  }

  const { isDragging, dragError, clearDragError, controls, canDrag, handleDragStart, handleDragEnd } = useSwipeToRemove({
    isRemoved,
    stateLoading,
    onSwipeComplete: handleSwipeComplete,
    url: slice?.url,
  })

  const swipeEnabled = canDrag && !isSelectMode

  if (!slice) return null

  const fullUrl = slice.url.startsWith('http://') || slice.url.startsWith('https://')
    ? slice.url
    : `https://${slice.url}`

  const { displayDomain, hostname } = (() => {
    try {
      const urlObj = new URL(fullUrl)
      const h = urlObj.hostname
      const d = h.replace(/^www\./, '').split('.')[0].toLowerCase()
      return { displayDomain: d, hostname: h }
    } catch {
      return { displayDomain: null, hostname: null }
    }
  })()

  const handleCardClick = (e) => {
    if (isDragging) return

    if (isRemoved) {
      e.preventDefault()
      return
    }

    const selection = window.getSelection()
    if (selection.toString().length > 0) return

    const shouldOpen = interactionActions.itemShortPress(componentId)
    if (shouldOpen) {
      summary.toggle()
    }
  }

  return (
    <Selectable id={componentId} disabled={isRemoved}>
      <motion.div
        layout
        className={`relative ${summary.expanded && !stateLoading ? 'mb-4' : 'mb-2.5'}`}
      >
        <div className={`absolute inset-0 rounded-xl bg-slate-100 flex items-center justify-end pr-8 pointer-events-none transition-opacity ${isDragging ? 'opacity-100' : 'opacity-0'}`}>
          <Trash2 className="text-slate-400" size={20} />
        </div>

        <motion.div
          drag={swipeEnabled ? "x" : false}
          dragConstraints={{ left: 0, right: 0 }}
          dragElastic={{ left: 0.5, right: 0.1 }}
          dragMomentum={false}
          dragListener={swipeEnabled}
          animate={controls}
          initial={{ opacity: 1, filter: 'grayscale(0%)', scale: 1, x: 0 }}
          transition={{ type: "spring", stiffness: 400, damping: 30 }}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          whileHover={swipeEnabled ? { scale: 1.005 } : undefined}
          whileTap={swipeEnabled ? { scale: 0.99 } : undefined}
          onClick={handleCardClick}
          style={{ touchAction: swipeEnabled ? "pan-y" : "auto" }}
          data-article-title={slice.title}
          data-article-url={slice.url}
          data-article-date={slice.issueDate}
          data-article-category={slice.category}
          data-article-source={slice.sourceId}
          data-read={isRead}
          data-removed={isRemoved}
          data-state-loading={stateLoading}
          data-summary-status={summary.status}
          data-summary-expanded={summary.expanded}
          data-summary-available={isAvailable}
          data-dragging={isDragging}
          data-can-drag={swipeEnabled}
          className={`
            relative z-10
            rounded-xl border border-slate-200/60
            shadow-card
            select-none
            ${isRemoved ? 'bg-slate-100/90 border-slate-200' : 'bg-white'}
            ${isRemoved ? 'cursor-default' : 'cursor-pointer'}
            ${stateLoading ? 'pointer-events-none' : ''}
            ${summary.expanded && !stateLoading ? 'ring-1 ring-brand-200/60 shadow-elevated' : ''}
          `}
        >
          <div className="p-4 flex items-center gap-3">
            <div className="flex flex-col gap-1.5 min-w-0 flex-1">
              <ArticleTitle
                isRead={isRead}
                title={slice.title}
              />

              {!isRemoved && (
                <ArticleMeta
                  hostname={hostname}
                  domain={displayDomain}
                  articleMeta={slice.articleMeta}
                />
              )}

              <span
                data-debug-article-url={slice.url}
                className="text-[10px] font-mono text-slate-300 truncate select-text"
                title={slice.url}
              >
                {slice.url}
              </span>

            {!isRemoved && summary.status === 'error' && (
              <SummaryError message={summary.errorMessage} />
            )}

            {!isRemoved && summary.expanded && (
              <ZenModeOverlay
                url={fullUrl}
                summaryMarkdown={summary.markdown}
                hostname={hostname}
                displayDomain={displayDomain}
                articleMeta={slice.articleMeta}
                onClose={() => handleSummaryClose()}
                onMarkRemoved={() => {
                  handleSummaryClose(false)
                  markAsRemoved()
                }}
              />
            )}
            </div>

            {isRemoved ? (
              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault()
                  event.stopPropagation()
                  toggleRemove()
                }}
                className="shrink-0 inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-slate-400 hover:text-slate-900"
                title="Restore article"
                aria-label={`Restore ${slice.title}`}
              >
                <Undo2 size={14} />
                <span>Restore</span>
              </button>
            ) : (
              isRead ? (
                <CheckCircle size={14} className="text-slate-300 shrink-0" />
              ) : isAvailable ? (
                <span className="w-2 h-2 rounded-full bg-brand-400 shrink-0" />
              ) : null
            )}
          </div>
        </motion.div>
      </motion.div>

      {dragError && <ErrorToast message={dragError} onDismiss={clearDragError} />}
    </Selectable>
  )
}

export default ArticleCard
