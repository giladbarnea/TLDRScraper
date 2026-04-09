import { motion } from 'framer-motion'
import { AlertCircle, CheckCircle, Trash2 } from 'lucide-react'
import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useInteraction } from '../contexts/InteractionContext'
import { useArticleState } from '../hooks/useArticleState'
import { useSummary } from '../hooks/useSummary'
import { useSwipeToRemove } from '../hooks/useSwipeToRemove'
import { subscribeToArticleAction } from '../lib/articleActionBus'
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

function ArticleMeta({ domain, hostname, articleMeta }) {
  return (
    <div className="flex items-center gap-2 min-w-0">
      {hostname && (
        <div className="w-4 h-4 rounded-full bg-white border border-slate-200 overflow-hidden flex items-center justify-center shrink-0">
          <img
            src={`https://www.google.com/s2/favicons?domain=${hostname}&sz=64`}
            alt={domain}
            className="w-full h-full object-cover"
            onError={(e) => { e.target.style.display = 'none' }}
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

function ArticleCard({ article }) {
  const { isSelectMode, registerDisabled, itemShortPress } = useInteraction()
  const { isRead, isRemoved, toggleRemove, markAsRemoved, loading: stateLoading } = useArticleState(
    article.issueDate,
    article.url
  )
  const summary = useSummary(article.issueDate, article.url)
  const { isAvailable } = summary

  const componentId = `article-${article.url}`

  const handleSwipeComplete = () => {
    if (!isRemoved && summary.expanded) summary.collapse()
    toggleRemove()
  }

  const { isDragging, dragError, clearDragError, controls, canDrag, handleDragStart, handleDragEnd } = useSwipeToRemove({
    isRemoved,
    stateLoading,
    onSwipeComplete: handleSwipeComplete,
    url: article.url,
  })

  const swipeEnabled = canDrag && !isSelectMode

  const fullUrl = article.url.startsWith('http://') || article.url.startsWith('https://')
    ? article.url
    : `https://${article.url}`

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
      toggleRemove()
      return
    }

    const selection = window.getSelection()
    if (selection.toString().length > 0) return

    const shouldOpen = itemShortPress(componentId)
    if (shouldOpen) {
      summary.toggle()
    }
  }

  useEffect(() => {
    registerDisabled(componentId, isRemoved)
    return () => registerDisabled(componentId, false)
  }, [componentId, isRemoved, registerDisabled])

  useEffect(() => {
    return subscribeToArticleAction(article.url, (action) => {
      if (isRemoved) return

      if (action === 'open-summary') {
        if (summary.isAvailable) summary.expand()
        return
      }

      if (action === 'fetch-summary') {
        if (summary.status === 'unknown' || summary.status === 'error') {
          summary.fetch()
        }
      }
    })
  }, [article.url, isRemoved, summary])

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
          data-article-title={article.title}
          data-article-url={article.url}
          data-article-date={article.issueDate}
          data-article-category={article.category}
          data-article-source={article.sourceId}
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
            cursor-pointer select-none
            ${isRemoved ? 'bg-slate-100/90 border-slate-200' : 'bg-white'}
            ${stateLoading ? 'pointer-events-none' : ''}
            ${summary.expanded && !stateLoading ? 'ring-1 ring-brand-200/60 shadow-elevated' : ''}
          `}
        >
          <div className="p-4 flex items-center gap-3">
            <div className="flex flex-col gap-1.5 min-w-0 flex-1">
              <ArticleTitle
                isRead={isRead}
                title={article.title}
              />

              {!isRemoved && (
                <ArticleMeta
                  domain={displayDomain}
                  hostname={hostname}
                  articleMeta={article.articleMeta}
                />
              )}

            {!isRemoved && summary.status === 'error' && (
              <SummaryError message={summary.errorMessage} />
            )}

            {!isRemoved && summary.expanded && summary.html && (
              <ZenModeOverlay
                url={fullUrl}
                html={summary.html}
                hostname={hostname}
                displayDomain={displayDomain}
                articleMeta={article.articleMeta}
                onClose={() => summary.collapse()}
                onMarkRemoved={() => {
                  summary.collapse(false)
                  markAsRemoved()
                }}
              />
            )}
            </div>

            {!isRemoved && (
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
