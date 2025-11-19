import { useMemo } from 'react'
import { useArticleState } from '../hooks/useArticleState'
import { useSummary } from '../hooks/useSummary'

function ArticleCard({ article, index }) {
  const { isRead, isRemoved, toggleRead, toggleRemove, markTldrHidden, unmarkTldrHidden, loading: stateLoading } = useArticleState(
    article.issueDate,
    article.url
  )

  const tldr = useSummary(article.issueDate, article.url, 'tldr')

  const fullUrl = useMemo(() => {
    const url = article.url
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url
    }
    return `https://${url}`
  }, [article.url])

  const handleLinkClick = (e) => {
    if (isRemoved) return
    if (e.ctrlKey || e.metaKey) return

    if (!isRead) {
      toggleRead()
    }
  }

  const handleTldrClick = (e) => {
    e.stopPropagation()
    if (isRemoved) return

    const wasExpanded = tldr.expanded
    tldr.toggle()

    if (!isRead && tldr.expanded) {
      toggleRead()
    }

    if (wasExpanded && !tldr.expanded) {
      markTldrHidden()
    } else if (tldr.expanded) {
      unmarkTldrHidden()
    }
  }

  const handleRemoveClick = (e) => {
    e.stopPropagation()
    if (!isRemoved && tldr.expanded) {
      tldr.collapse()
    }
    toggleRemove()
  }

  const cardClasses = `group relative bg-white transition-all duration-300 border border-slate-100 rounded-2xl shadow-soft hover:shadow-soft-hover mb-4 overflow-hidden ${tldr.expanded ? 'ring-1 ring-brand-100 shadow-soft-hover' : ''} ${isRemoved ? 'opacity-60 bg-slate-50 border-dashed' : 'hover:-translate-y-0.5'} ${isRead && !isRemoved ? 'bg-slate-50/40' : ''}`

  const titleClasses = `text-[18px] font-display font-bold leading-snug transition-colors duration-200 block ${isRemoved ? 'text-slate-400 line-through' : 'text-slate-900 group-hover:text-brand-600 cursor-pointer'} ${isRead && !isRemoved ? 'text-slate-600 font-medium' : ''}`

  return (
    <div className={cardClasses}>
      <div className="p-5 flex flex-col gap-3">

        {/* Header Meta */}
        <div className="flex items-center justify-between">
           <div className="flex items-center gap-2">
             <span className="text-xs font-bold text-slate-300 font-mono">#{index + 1}</span>
             {!isRemoved && article.articleMeta && (
               <span className="text-[10px] font-bold tracking-wider uppercase text-brand-600 bg-brand-50 px-2 py-0.5 rounded-full border border-brand-100">
                  {article.articleMeta}
               </span>
             )}
           </div>
        </div>

        {/* Title Content */}
        <div className="flex-1">
          <a
            href={fullUrl}
            className={titleClasses}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleLinkClick}
          >
            {article.title}
          </a>
        </div>

        {/* Actions Bar */}
        <div className="flex items-center justify-between pt-2 mt-1">
          <button
            onClick={handleTldrClick}
            disabled={stateLoading || tldr.loading}
            className={`
              flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold tracking-wide transition-all duration-200
              ${tldr.expanded
                ? 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                : 'bg-slate-50 text-brand-600 hover:bg-brand-50 hover:text-brand-700 border border-slate-100 hover:border-brand-100'}
              ${isRemoved ? 'invisible' : ''}
            `}
          >
            {tldr.loading ? (
              <span className="flex items-center gap-1.5"><i data-lucide="loader-2" className="w-3.5 h-3.5 animate-spin"></i> Generating...</span>
            ) : tldr.expanded ? (
              <span className="flex items-center gap-1.5"><i data-lucide="minimize-2" className="w-3.5 h-3.5"></i> Minimize</span>
            ) : (
              <span className="flex items-center gap-1.5"><i data-lucide="sparkles" className="w-3.5 h-3.5"></i> TLDR</span>
            )}
          </button>

          <button
            onClick={handleRemoveClick}
            className={`
              p-2 rounded-full transition-all
              ${isRemoved
                ? 'bg-red-50 text-red-600 hover:bg-red-100 px-3 text-xs font-bold w-auto'
                : 'text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100'}
            `}
            title={isRemoved ? 'Restore' : 'Remove'}
          >
            {isRemoved ? (
              <span className="flex items-center gap-1">Restore</span>
            ) : (
              <i data-lucide="trash-2" className="w-4 h-4"></i>
            )}
          </button>
        </div>

        {/* TLDR Content */}
        {tldr.expanded && (
          <div className="animate-slide-up mt-5 pt-5 border-t border-slate-100/80">
             <div className="flex items-center gap-2 mb-3">
                <div className="bg-brand-100 p-1 rounded-md">
                   <i data-lucide="bot" className="w-3.5 h-3.5 text-brand-600"></i>
                </div>
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Quick Summary</span>
             </div>

             {tldr.errorMessage ? (
               <div className="text-sm text-red-500 bg-red-50 p-3 rounded-xl border border-red-100">
                 {tldr.errorMessage}
               </div>
             ) : (
               <div
                  className="prose prose-sm max-w-none prose-p:text-slate-600 prose-p:leading-relaxed prose-li:text-slate-600 prose-strong:text-slate-800 prose-ul:my-2"
                  dangerouslySetInnerHTML={{ __html: tldr.html }}
               />
             )}
          </div>
        )}

      </div>
    </div>
  )
}

export default ArticleCard
