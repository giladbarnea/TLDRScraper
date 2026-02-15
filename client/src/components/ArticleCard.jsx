import { motion } from 'framer-motion'
import { AlertCircle, ArrowDownCircle, Check, CheckCircle, ChevronDown, Loader2, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useInteraction } from '../contexts/InteractionContext'
import { useArticleState } from '../hooks/useArticleState'
import { useOverscrollUp } from '../hooks/useOverscrollUp'
import { usePullToClose } from '../hooks/usePullToClose'
import { useScrollProgress } from '../hooks/useScrollProgress'
import { useSummary } from '../hooks/useSummary'
import { useSwipeToRemove } from '../hooks/useSwipeToRemove'
import { useTouchPhase } from '../hooks/useTouchPhase'
import Selectable from './Selectable'

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

function ZenModeOverlay({ url, html, hostname, displayDomain, articleMeta, onClose, onMarkRemoved }) {
  const [hasScrolled, setHasScrolled] = useState(false)
  const containerRef = useRef(null)
  const scrollRef = useRef(null)
  const progress = useScrollProgress(scrollRef)
  const { pullOffset } = usePullToClose({ containerRef, scrollRef, onClose })
  const { overscrollOffset, isOverscrolling, progress: overscrollProgress, isComplete: overscrollComplete } = useOverscrollUp({
    scrollRef,
    onComplete: onMarkRemoved,
    threshold: 60
  })

  const truncatedMeta = articleMeta && articleMeta.length > 22
    ? `${articleMeta.slice(0, 22)}...`
    : articleMeta

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)

    const scrollEl = scrollRef.current
    const handleScroll = () => {
      setHasScrolled(scrollEl.scrollTop > 10)
    }
    scrollEl?.addEventListener('scroll', handleScroll, { passive: true })

    return () => {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', handleEscape)
      scrollEl?.removeEventListener('scroll', handleScroll)
    }
  }, [onClose])

  return createPortal(
    <div
      className="fixed inset-0 z-[100]"
      style={{
        transform: `translateY(${pullOffset}px)`,
        transition: pullOffset === 0 ? 'transform 0.3s ease-out' : 'none'
      }}
    >
      <div ref={containerRef} className="w-full h-full bg-white flex flex-col animate-zen-enter">
        {/* Header */}
        <div
          className={`
            relative shrink-0 z-10
            flex items-center justify-between px-4 py-3
            transition-all duration-200
            ${hasScrolled ? 'bg-white/80 backdrop-blur-md border-b border-slate-200/60' : 'bg-white'}
          `}
        >
          <button
            onClick={onClose}
            className="shrink-0 p-2 rounded-full hover:bg-slate-200/80 text-slate-500 hover:text-slate-700 transition-colors"
          >
            <ChevronDown size={20} />
          </button>

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

          <button
            onClick={onMarkRemoved}
            className="shrink-0 p-2 rounded-full hover:bg-green-100 text-slate-500 hover:text-green-600 transition-colors"
          >
            <Check size={20} />
          </button>

          {/* Progress Bar */}
          <div
            className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-500 origin-left transition-transform duration-100"
            style={{ transform: `scaleX(${progress})` }}
          />
        </div>

        {/* Content Area */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto bg-white">
          <div
            className="px-6 pt-2 pb-5 md:px-8 md:pt-3 md:pb-6"
            style={{
              transform: `translateY(-${overscrollOffset * 0.4}px)`,
              transition: isOverscrolling ? 'none' : 'transform 0.2s ease-out'
            }}
          >
            <div className="max-w-3xl mx-auto">
              <div
                className="prose prose-slate max-w-none font-serif text-slate-700 leading-relaxed text-lg prose-p:my-3 prose-headings:text-slate-900 prose-headings:tracking-tight prose-h1:text-2xl prose-h1:font-bold prose-h2:text-xl prose-h2:font-semibold prose-h3:text-lg prose-h3:font-semibold prose-blockquote:border-slate-200 prose-strong:text-slate-900"
                dangerouslySetInnerHTML={{ __html: html }}
              />
            </div>
          </div>

          {/* Overscroll completion zone */}
          <div
            className={`
              flex items-center justify-center py-16 transition-all duration-150
              ${isOverscrolling ? 'opacity-100' : 'opacity-0'}
            `}
            style={{
              transform: `translateY(${isOverscrolling ? 0 : 20}px)`,
            }}
          >
            <div
              className={`
                w-12 h-12 rounded-full flex items-center justify-center transition-all duration-150
                ${overscrollComplete
                  ? 'bg-green-500 text-white scale-110'
                  : 'bg-slate-100 text-slate-400'}
              `}
            >
              <CheckCircle
                size={24}
                style={{
                  opacity: 0.3 + overscrollProgress * 0.7,
                  transform: `scale(${0.8 + overscrollProgress * 0.2})`
                }}
              />
            </div>
          </div>
        </div>
      </div>
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

function ArticleMeta({ domain, hostname, articleMeta, summaryLoading, summaryAvailable, isRead }) {
  const stateIndicator = summaryLoading ? (
    <Loader2 size={14} className="animate-spin text-brand-500 shrink-0" />
  ) : isRead ? (
    <CheckCircle size={14} className="text-slate-300 shrink-0" />
  ) : summaryAvailable ? (
    <ArrowDownCircle size={14} className="text-slate-300 shrink-0" />
  ) : null

  return (
    <div className="flex items-center justify-between gap-2">
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
      {stateIndicator}
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

  const { touchPhase, pointerHandlers } = useTouchPhase({
    isSelectMode,
    isRemoved,
    isDragging,
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
      console.log('[touch-phase] click: delaying summary.toggle() by 2s')
      setTimeout(() => summary.toggle(), 2000)
    }
  }

  useEffect(() => {
    registerDisabled(componentId, isRemoved)
    return () => registerDisabled(componentId, false)
  }, [componentId, isRemoved, registerDisabled])

  return (
    <Selectable id={componentId} disabled={isRemoved}>
      <motion.div
        layout
        className={`relative ${summary.expanded && !stateLoading ? 'mb-4' : 'mb-2.5'}`}
      >
        <div className={`absolute inset-0 rounded-xl bg-red-50 flex items-center justify-end pr-8 pointer-events-none transition-opacity ${isDragging ? 'opacity-100' : 'opacity-50'}`}>
          <Trash2 className="text-red-400" size={20} />
        </div>

        <motion.div
          {...pointerHandlers}
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
          data-touch-phase={touchPhase}
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
            ${isRemoved ? 'bg-slate-50' : 'bg-white'}
            ${stateLoading ? 'pointer-events-none' : ''}
            ${summary.expanded && !stateLoading ? 'ring-1 ring-brand-200/60 shadow-elevated' : ''}
          `}
        >
          <div className="p-4 flex flex-col gap-1.5">
            <ArticleTitle
              isRead={isRead}
              title={article.title}
            />

            {!isRemoved && (
              <ArticleMeta
                domain={displayDomain}
                hostname={hostname}
                articleMeta={touchPhase}
                summaryLoading={summary.loading}
                summaryAvailable={isAvailable}
                isRead={isRead}
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
        </motion.div>
      </motion.div>

      {dragError && <ErrorToast message={dragError} onDismiss={clearDragError} />}
    </Selectable>
  )
}

export default ArticleCard
