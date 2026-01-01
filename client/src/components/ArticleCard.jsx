import { motion } from 'framer-motion'
import { AlertCircle, Check, CheckCircle, ChevronDown, Loader2, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useArticleState } from '../hooks/useArticleState'
import { useScrollProgress } from '../hooks/useScrollProgress'
import { useSummary } from '../hooks/useSummary'
import { useSwipeDown } from '../hooks/useSwipeDown'
import { useSwipeToRemove } from '../hooks/useSwipeToRemove'

function ErrorToast({ message, onDismiss }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000)
    return () => clearTimeout(timer)
  }, [onDismiss])

  return createPortal(
    <div className="fixed bottom-4 left-4 right-4 z-[200] bg-red-600 text-white p-4 rounded-xl shadow-lg flex items-start gap-3">
      <AlertCircle size={20} className="shrink-0 mt-0.5" />
      <div className="flex-1 text-sm font-medium break-all">{message}</div>
      <button onClick={onDismiss} className="shrink-0 text-white/80 hover:text-white">✕</button>
    </div>,
    document.body
  )
}

function ZenModeOverlay({ url, html, hostname, displayDomain, articleMeta, onClose, onMarkDone }) {
  const [hasScrolled, setHasScrolled] = useState(false)
  const scrollRef = useRef(null)
  const progress = useScrollProgress(scrollRef)
  const { controls, handlePointerDown, handlePointerMove, handlePointerUp } = useSwipeDown({
    onSwipeComplete: onClose,
    scrollRef
  })

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
    <div className="fixed inset-0 z-[100]">
      <motion.div
        animate={controls}
        initial={{ y: 20, opacity: 0 }}
        className="w-full h-full bg-white"
      >
        <div
          ref={scrollRef}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          className="overflow-y-auto h-full bg-white"
        >
          {/* Sticky Header */}
          <div
            className={`
              sticky top-0 z-10
              flex items-center justify-between p-4
              transition-all duration-200
              ${hasScrolled ? 'bg-white/95 backdrop-blur-md border-b border-slate-100' : 'bg-white'}
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
                  className="w-[18px] h-[18px] rounded-full border border-slate-200"
                  alt=""
                />
              )}
              <span className="text-sm text-slate-500 font-medium">
                {displayDomain}
                {articleMeta && <span className="text-slate-400"> · {articleMeta}</span>}
              </span>
            </a>

            <button
              onClick={onMarkDone}
              className="shrink-0 p-2 rounded-full hover:bg-green-100 text-slate-500 hover:text-green-600 transition-colors"
            >
              <Check size={20} />
            </button>

            {/* Progress Bar */}
            <div
              className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-500 origin-left transition-transform duration-100"
              style={{ transform: `scaleX(${progress})` }}
            />
          </div>

          {/* Content Area - flows after header */}
          <div className="px-6 pb-6 md:px-8 md:pb-8 bg-white">
            <div className="max-w-3xl mx-auto">
              <div
                className="prose prose-slate max-w-none font-serif text-slate-700 leading-relaxed text-lg prose-p:my-3 prose-headings:text-slate-900"
                dangerouslySetInnerHTML={{ __html: html }}
              />
            </div>
          </div>
        </div>
      </motion.div>
    </div>,
    document.body
  )
}

function ArticleTitle({ isRead, title }) {
  return (
    <span
      className={`
        text-[17px] font-display font-semibold leading-snug text-slate-900
        block tracking-tight
        ${isRead ? 'text-slate-500 font-normal' : ''}
      `}
    >
      {title}
    </span>
  )
}

function ArticleMeta({ domain, hostname, articleMeta, isRead, tldrLoading }) {
  return (
    <div className="mb-1 flex items-center justify-between">
      <div className="flex items-center gap-2">
        {hostname && (
          <div className="w-[18px] h-[18px] rounded-full bg-white border border-slate-200 overflow-hidden flex items-center justify-center shrink-0">
            <img
              src={`https://www.google.com/s2/favicons?domain=${hostname}&sz=64`}
              alt={domain}
              className="w-full h-full object-cover"
              onError={(e) => { e.target.style.display = 'none' }}
            />
          </div>
        )}
        <div className="flex items-baseline gap-2 text-xs leading-none">
          <span className="font-medium text-slate-600">
            {domain && domain}
          </span>
          <span className="text-slate-300">|</span>
          <span className="font-normal text-slate-400">
            {articleMeta}
          </span>
        </div>
        {isRead && <CheckCircle size={14} className="text-slate-300" />}
      </div>
      {tldrLoading && <Loader2 size={14} className="animate-spin text-brand-500" />}
    </div>
  )
}

function TldrError({ message }) {
  return (
    <div className="mt-4 text-xs text-red-500 bg-red-50 p-3 rounded-lg">
      {message || 'Failed to load summary.'}
    </div>
  )
}

function ArticleCard({ article }) {
  const { isRead, isRemoved, toggleRemove, loading: stateLoading } = useArticleState(
    article.issueDate,
    article.url
  )
  const tldr = useSummary(article.issueDate, article.url, 'tldr')
  const { isAvailable } = tldr

  const handleSwipeComplete = () => {
    if (!isRemoved && tldr.expanded) tldr.collapse()
    toggleRemove()
  }

  const { isDragging, dragError, clearDragError, controls, canDrag, handleDragStart, handleDragEnd } = useSwipeToRemove({
    isRemoved,
    stateLoading,
    onSwipeComplete: handleSwipeComplete,
  })

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

    tldr.toggle()
  }

  return (
    <>
      <motion.div
        layout
        className={`relative ${tldr.expanded && !stateLoading ? 'mb-6' : 'mb-3'}`}
      >
        <div className={`absolute inset-0 rounded-[20px] bg-red-50 flex items-center justify-end pr-8 transition-opacity ${isDragging ? 'opacity-100' : 'opacity-50'}`}>
          <Trash2 className="text-red-400" size={20} />
        </div>

        <motion.div
          drag={canDrag ? "x" : false}
          dragConstraints={{ left: 0, right: 0 }}
          dragElastic={{ left: 0.5, right: 0.1 }}
          dragMomentum={false}
          dragListener={canDrag}
          animate={controls}
          initial={{ opacity: 1, filter: 'grayscale(0%)', scale: 1, x: 0 }}
          transition={{ type: "spring", stiffness: 400, damping: 30 }}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          whileHover={canDrag ? { scale: 1.005 } : undefined}
          whileTap={canDrag ? { scale: 0.99 } : undefined}
          onClick={handleCardClick}
          style={{ touchAction: canDrag ? "pan-y" : "auto" }}
          data-article-title={article.title}
          data-article-url={article.url}
          data-article-date={article.issueDate}
          data-article-category={article.category}
          data-article-source={article.sourceId}
          data-read={isRead}
          data-removed={isRemoved}
          data-state-loading={stateLoading}
          data-tldr-status={tldr.status}
          data-tldr-expanded={tldr.expanded}
          data-tldr-available={isAvailable}
          data-dragging={isDragging}
          data-can-drag={canDrag}
          className={`
            relative z-10
            rounded-[20px] border border-white/40
            shadow-[0_2px_12px_-4px_rgba(0,0,0,0.05)]
            backdrop-blur-xl
            cursor-pointer select-none
            ${isRemoved ? 'bg-slate-50' : 'bg-white'}
            ${stateLoading ? 'pointer-events-none' : ''}
            ${tldr.expanded && !stateLoading ? 'ring-1 ring-brand-100 shadow-md' : ''}
          `}
        >
          <div className="p-5 flex flex-col gap-2">
            <ArticleTitle
              isRead={isRead}
              title={article.title}
            />

            {!isRemoved && (
              <ArticleMeta
                domain={displayDomain}
                hostname={hostname}
                articleMeta={article.articleMeta}
                isRead={isRead}
                tldrLoading={tldr.loading}
              />
            )}

            {!isRemoved && tldr.status === 'error' && (
              <TldrError message={tldr.errorMessage} />
            )}

            {!isRemoved && tldr.expanded && tldr.html && (
              <ZenModeOverlay
                url={fullUrl}
                html={tldr.html}
                hostname={hostname}
                displayDomain={displayDomain}
                articleMeta={article.articleMeta}
                onClose={() => tldr.collapse()}
                onMarkDone={() => {
                  tldr.collapse()
                  toggleRemove()
                }}
              />
            )}
          </div>
        </motion.div>
      </motion.div>
      
      {dragError && <ErrorToast message={dragError} onDismiss={clearDragError} />}
    </>
  )
}

export default ArticleCard
