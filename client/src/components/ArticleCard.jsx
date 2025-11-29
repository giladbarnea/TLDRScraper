import { CheckCircle, Loader2, Minus, Sparkles, Trash2 } from 'lucide-react'
import { useMemo, } from 'react'
import { useArticleState } from '../hooks/useArticleState'
import { useSummary } from '../hooks/useSummary'
import { cn } from '../lib/utils'

function ArticleCard({ article }) {
  const issueDate = article.issueDate

  const { isRead, isRemoved, toggleRead, toggleRemove, loading: stateLoading } = useArticleState(
    issueDate,
    article.url
  )
  const tldr = useSummary(issueDate, article.url, 'tldr')
  const { isAvailable, toggleVisibility } = tldr

  const fullUrl = useMemo(() => {
    const url = article.url
    if (url.startsWith('http://') || url.startsWith('https://')) return url
    return `https://${url}`
  }, [article.url])

  if (!issueDate) {
    console.error('ArticleCard: Missing issueDate field', article)
    return null
  }

  const handleExpand = async (e) => {
    e.stopPropagation();
    if (isRemoved) return;

    tldr.toggle();

    if (!isRead && !tldr.expanded) {
       toggleRead()
    }
  };

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

    if (isAvailable) {
      toggleVisibility()
    }
  };

  return (
    <div
      onClick={handleCardClick}
      data-testid={`article-card-${article.url}`}
      className={cn(
        "group relative transition-all duration-300 ease-out rounded-[20px] border",
        
        // Base state (Default)
        "bg-white/80 backdrop-blur-xl border-white/40 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_20px_-4px_rgba(0,0,0,0.08)] hover:-translate-y-0.5 mb-3",

        // Loading state
        stateLoading && "opacity-40 grayscale pointer-events-none bg-slate-50 border-slate-200",

        // Removed state
        isRemoved && "opacity-50 grayscale scale-[0.98] bg-slate-50 border-transparent cursor-pointer hover:opacity-60",

        // Expanded state
        tldr.expanded && !stateLoading && "mb-6 ring-1 ring-brand-100 shadow-md bg-white",

        // Interactive cursor
        !isRemoved && isAvailable && "cursor-pointer"
      )}
    >
      <div className="p-5 flex flex-col gap-2">
         {/* Title */}
         <a
           href={isRemoved ? undefined : fullUrl}
           data-testid={`article-title-${article.url}`}
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
           <div className="mb-1">
               <span className="text-[11px] font-medium text-slate-400">
                  {article.articleMeta || 'Today'}
               </span>
               {isRead && <CheckCircle size={14} className="text-slate-300 inline ml-2" />}
           </div>
         )}

         {/* Actions */}
         {!isRemoved && (
           <div className="flex items-center justify-between pt-3">
              <button
                onClick={handleExpand}
                disabled={tldr.loading}
                className={cn(
                  "flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-wide transition-all duration-300",
                  
                  // Default (Invite)
                  "bg-slate-50 text-slate-500 hover:bg-brand-50 hover:text-brand-600",

                  // Available (Magic Tint)
                  !tldr.loading && !tldr.expanded && isAvailable && "bg-indigo-50 text-indigo-600 ring-1 ring-inset ring-indigo-200/50 hover:bg-indigo-100",

                  // Expanded
                  !tldr.loading && tldr.expanded && "bg-slate-100 text-slate-600 hover:bg-slate-200",

                  // Loading
                  tldr.loading && "bg-slate-50 text-slate-400"
                )}
              >
                 {tldr.loading ? <Loader2 size={14} className="animate-spin" /> :
                  tldr.expanded ? <><Minus size={14} /> Close</> : <><Sparkles size={14} /> TLDR</>
                 }
              </button>

              <div className="flex gap-2">
                  <button
                    onClick={handleRemove}
                    data-testid={`remove-button-${article.url}`}
                    disabled={stateLoading}
                    className={`p-1.5 rounded-full transition-colors ${stateLoading ? 'text-slate-300 cursor-not-allowed' : 'text-slate-400 hover:text-red-500 hover:bg-red-50'}`}
                  >
                     <Trash2 size={14} />
                  </button>
              </div>
           </div>
         )}

         {/* TLDR Content */}
         {!isRemoved && (
           <div
              className={`
                transition-all duration-500 ease-[cubic-bezier(0.25,0.1,0.25,1.0)]
                ${tldr.expanded && tldr.html ? 'opacity-100 mt-4 border-t border-slate-100 pt-5' : 'max-h-0 opacity-0 overflow-hidden -mt-3 invisible'}
              `}
           >
              {/* -mt-3 cancels parent's gap-3 to eliminate spacing when collapsed */}
              {tldr.status === 'error' ? (
                 <div className="text-xs text-red-500 bg-red-50 p-3 rounded-lg">{tldr.errorMessage || 'Failed to load summary.'}</div>
              ) : (
                 <div className="animate-fade-in">
                    <div
                      className="prose prose-sm prose-slate max-w-none font-sans text-slate-600 leading-relaxed text-[15px] prose-p:my-2"
                      dangerouslySetInnerHTML={{ __html: tldr.html }}
                    />
                 </div>
              )}
           </div>
         )}
      </div>
    </div>
  )
}

export default ArticleCard
