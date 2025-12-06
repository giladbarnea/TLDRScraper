import { CheckCircle, ChevronLeft, Loader2, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useArticleState } from '../hooks/useArticleState'
import { useScrollProgress } from '../hooks/useScrollProgress'
import { useSummary } from '../hooks/useSummary'

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
    <div className="fixed inset-0 z-[100] bg-black/50 backdrop-blur-sm animate-zen-enter">
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

function ArticleCard({ article }) {
  const { isRead, isRemoved, toggleRead, toggleRemove, markTldrHidden, unmarkTldrHidden, loading: stateLoading } = useArticleState(
    article.issueDate,
    article.url
  )
  const tldr = useSummary(article.issueDate, article.url, 'tldr')
  const { isAvailable, toggleVisibility } = tldr

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



  const handleRemove = (e) => {
    e.stopPropagation();
    if (!isRemoved && tldr.expanded) tldr.collapse();
    toggleRemove();
  };

  const handleCardClick = (e) => {
    if (isRemoved) {
      e.preventDefault();
      toggleRemove();
      return;
    }

    // If text is selected, don't trigger the click
    const selection = window.getSelection();
    if (selection.toString().length > 0) return;

    toggleTldrWithTracking(() => tldr.toggle());
  };

  return (
    <div
      onClick={handleCardClick}
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
      className={`
        group relative transition-all duration-300 ease-out
        rounded-[20px] border
        ${stateLoading
          ? 'opacity-40 grayscale pointer-events-none bg-slate-50 border-slate-200'
          : isRemoved
            ? 'opacity-50 grayscale scale-[0.98] bg-slate-50 border-transparent cursor-pointer hover:opacity-60'
            : 'bg-white/80 backdrop-blur-xl border-white/40 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_20px_-4px_rgba(0,0,0,0.08)] hover:-translate-y-0.5 cursor-pointer'}
        ${tldr.expanded && !stateLoading ? 'mb-6 ring-1 ring-brand-100 shadow-md bg-white' : 'mb-3'}
      `}
    >
      <div className="p-5 flex flex-col gap-2">
        {/* Title */}
        <a
          href={isRemoved ? undefined : fullUrl}
          target={isRemoved ? undefined : "_blank"}
          rel={isRemoved ? undefined : "noopener noreferrer"}
          className={`
            text-[17px] font-display font-semibold leading-snug text-slate-900
            hover:text-brand-600 transition-colors duration-200 block tracking-tight
            ${isRead ? 'text-slate-500 font-normal' : ''}
            ${isRemoved ? 'pointer-events-none' : ''}
          `}
          onClick={(e) => {
            if (isRemoved) {
              e.preventDefault();
              return;
            }
            e.stopPropagation();
            if (!isRead) toggleRead();
          }}
        >
          {article.title}
        </a>

        {/* Header */}
        {!isRemoved && (
          <div className="mb-1 flex items-center justify-between">
              <div className="flex items-center gap-2">
              <span className="text-[11px] font-medium text-slate-400">
                  {domain && domain}
                  {domain && article.articleMeta && ' │ '}
                  {article.articleMeta}
              </span>
              {isRead && <CheckCircle size={14} className="text-slate-300" />}
              </div>
              
              {/* Loading Indicator or Status Icon could go here if needed, but keeping it clean for now */}
              {tldr.loading && <Loader2 size={14} className="animate-spin text-brand-500" />}
          </div>
        )}

        {/* Actions - Just the delete button now, positioned absolutely or bottom right? 
            The original design had a row. Let's keep the row but simplified.
        */}
        {!isRemoved && (
          <div className="flex items-center justify-end pt-2">
              <button
                onClick={handleRemove}
                disabled={stateLoading}
                className={`p-1.5 rounded-full transition-colors ${stateLoading ? 'text-slate-300 cursor-not-allowed' : 'text-slate-400 hover:text-red-500 hover:bg-red-50'}`}
              >
                <Trash2 size={14} />
              </button>
          </div>
        )}

         {/* TLDR Error State (inline) */}
         {!isRemoved && tldr.status === 'error' && (
           <div className="mt-4 text-xs text-red-500 bg-red-50 p-3 rounded-lg">
             {tldr.errorMessage || 'Failed to load summary.'}
           </div>
         )}

         {/* Zen Mode Overlay for TLDR Content */}
         {!isRemoved && tldr.expanded && tldr.html && (
           <ZenModeOverlay
             title={article.title}
             html={tldr.html}
             onClose={() => toggleTldrWithTracking(() => tldr.collapse())}
           />
         )}
      </div>
    </div>
  )
}

export default ArticleCard
