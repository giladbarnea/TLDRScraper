import { CheckCircle, ChevronLeft, Loader2, Trash2, AlertCircle } from 'lucide-react'
import { useEffect, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'
import { motion } from 'framer-motion'
import { useArticleState } from '../hooks/useArticleState'
import { useScrollProgress } from '../hooks/useScrollProgress'
import { useSummary } from '../hooks/useSummary'
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

function ZenModeOverlay({ title, html, onClose }) {
  const scrollRef = useRef(null)
  const progress = useScrollProgress(scrollRef)

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', handleEscape)
    }
  }, [onClose])

  return createPortal(
    <div className="fixed inset-0 z-[100]">
      <div className="w-full h-full bg-white flex flex-col animate-zen-enter">
        <div className="flex items-center gap-3 p-5 border-b border-slate-100 bg-slate-50/80 shrink-0">
          <button
            onClick={onClose}
            className="shrink-0 p-2 rounded-full hover:bg-slate-200 text-slate-500 hover:text-slate-700 transition-colors"
          >
            <ChevronLeft size={20} />
          </button>
          <h2 className="font-display font-semibold text-lg text-slate-800">
            {title}
          </h2>
        </div>
        <div
          className="h-0.5 bg-purple-500 origin-left transition-transform duration-100"
          style={{ transform: `scaleX(${progress})` }}
        />
        <div ref={scrollRef} className="overflow-y-auto flex-1 p-6 md:p-8 bg-white">
          <div className="max-w-3xl mx-auto">
            <div
              className="prose prose-slate max-w-none font-serif text-slate-700 leading-relaxed text-lg prose-p:my-3 prose-headings:text-slate-900"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}

function ArticleTitle({ href, isRemoved, isRead, title, onLinkClick }) {
  return (
    <a
      href={isRemoved ? undefined : href}
      target={isRemoved ? undefined : "_blank"}
      rel={isRemoved ? undefined : "noopener noreferrer"}
      className={`
        text-[17px] font-display font-semibold leading-snug text-slate-900
        hover:text-brand-600 transition-colors duration-200 block tracking-tight
        ${isRead ? 'text-slate-500 font-normal' : ''}
        ${isRemoved ? 'pointer-events-none' : ''}
      `}
      onClick={onLinkClick}
    >
      {title}
    </a>
  )
}

function ArticleMeta({ domain, articleMeta, isRead, tldrLoading }) {
  return (
    <div className="mb-1 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-medium text-slate-400">
          {domain && domain}
          {domain && articleMeta && ' │ '}
          {articleMeta}
        </span>
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
  const { isRead, isRemoved, toggleRead, toggleRemove, markTldrHidden, unmarkTldrHidden, loading: stateLoading } = useArticleState(
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

  const fullUrl = useMemo(() => {
    const url = article.url
    if (url.startsWith('http://') || url.startsWith('https://')) return url
    return `https://${url}`
  }, [article.url])

  const domain = useMemo(() => {
    try {
      const urlObj = new URL(fullUrl)
      const hostname = urlObj.hostname
      return hostname.replace(/^www\./, '').split('.')[0].toLowerCase()
    } catch {
      return null
    }
  }, [fullUrl])

  const toggleTldrWithTracking = (toggleFn) => {
    const wasExpanded = tldr.expanded
    toggleFn()

    if (wasExpanded) {
      markTldrHidden()
    } else {
      unmarkTldrHidden()
    }
  }

  const handleCardClick = (e) => {
    if (isDragging) return
    
    if (isRemoved) {
      e.preventDefault()
      toggleRemove()
      return
    }

    const selection = window.getSelection()
    if (selection.toString().length > 0) return

    toggleTldrWithTracking(() => tldr.toggle())
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
              href={fullUrl}
              isRemoved={isRemoved}
              isRead={isRead}
              title={article.title}
              onLinkClick={(e) => {
                if (isDragging || isRemoved) {
                  e.preventDefault()
                  return
                }
                e.stopPropagation()
                if (!isRead) toggleRead()
              }}
            />

            {!isRemoved && (
              <ArticleMeta
                domain={domain}
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
                title={article.title}
                html={tldr.html}
                onClose={() => toggleTldrWithTracking(() => tldr.collapse())}
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
