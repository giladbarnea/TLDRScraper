import { Loader2 } from 'lucide-react'
import { useSupabaseStorage } from '../hooks/useSupabaseStorage'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import ArticleList from './ArticleList'

function ResultsDisplay({ results }) {
  const statsLines = [
    `${results.stats.total_articles} Articles`,
    `${results.stats.unique_urls} Sources`,
    results.source === 'local cache' ? 'Cached' : 'Live'
  ]

  const debugLogs = results.debugLogs || []

  return (
    <div className="animate-slide-up pb-20">
      {/* Stats Pills */}
      <div className="flex flex-wrap gap-2 mb-8 justify-center">
        {statsLines.map((line, index) => (
          <span key={index} className="px-3 py-1 bg-slate-100 text-slate-500 rounded-full text-[10px] font-bold uppercase tracking-wider border border-slate-200/60">
            {line}
          </span>
        ))}
      </div>

      {debugLogs.length > 0 && (
        <div className="mb-8 text-center">
          <details className="group inline-block">
            <summary className="list-none cursor-pointer text-[10px] font-bold text-slate-300 uppercase tracking-widest hover:text-brand-500 transition-colors">
              View Debug Logs
            </summary>
            <div className="mt-4 text-left">
               <pre className="p-4 bg-slate-900 text-slate-400 rounded-xl text-[10px] overflow-x-auto font-mono shadow-inner max-h-60 scrollbar-thin">
                 {debugLogs.join('\n')}
               </pre>
            </div>
          </details>
        </div>
      )}

      <div className="space-y-16">
        {(results.payloads || []).map((payload) => (
          <DailyResults
            key={payload.date}
            payload={payload}
          />
        ))}
      </div>
    </div>
  )
}

function DailyResults({ payload }) {
  const [livePayload, , , { loading }] = useSupabaseStorage(
    getNewsletterScrapeKey(payload.date),
    payload
  )

  const date = livePayload?.date ?? payload.date
  const articles = (livePayload?.articles ?? payload.articles).map((article, index) => ({
    ...article,
    originalOrder: index
  }))
  const issues = livePayload?.issues ?? payload.issues ?? []

  const dateObj = new Date(date)
  const formattedDate = dateObj.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })

  return (
    <section className="relative">
      {/* Sticky Date Header */}
      <div className="sticky top-24 z-30 flex justify-center mb-8 pointer-events-none">
        <div className="bg-slate-900/90 backdrop-blur-md text-white pl-5 pr-5 py-2 rounded-full shadow-soft-hover pointer-events-auto ring-1 ring-white/20">
          <h2 className="text-sm font-bold font-display tracking-wide flex items-center gap-2">
            {formattedDate}
            {loading && <Loader2 className="w-3 h-3 animate-spin opacity-70" />}
          </h2>
        </div>
      </div>

      <div className="bg-white/40 backdrop-blur-sm rounded-[2rem] p-2 sm:p-6 border border-slate-100/60 shadow-sm">
        {issues.map((issue) => (
          <div key={`${date}-${issue.category}`} className="mb-10 last:mb-0">
            {/* Issue Category Header */}
            <div className="flex items-center gap-4 mb-6 pl-2 mt-2">
               <div className="h-px flex-1 bg-slate-200/60"></div>
               <h4 className="font-display font-bold text-xl text-slate-800 tracking-tight">
                 {issue.category}
               </h4>
               <div className="h-px flex-1 bg-slate-200/60"></div>
            </div>

            {(issue.title || issue.subtitle) && (
              <div className="text-center mb-8 px-4 max-w-lg mx-auto">
                {issue.title && (
                  <p className="text-base font-medium text-slate-700 italic font-serif">"{issue.title}"</p>
                )}
                {issue.subtitle && issue.subtitle !== issue.title && (
                  <p className="text-xs text-slate-400 mt-2 font-medium uppercase tracking-wide">{issue.subtitle}</p>
                )}
              </div>
            )}

            <ArticleList
              articles={articles.filter((article) => article.category === issue.category)}
            />
          </div>
        ))}

        {articles.some((article) => !article.category) && (
          <ArticleList
            articles={articles.filter((article) => !article.category)}
          />
        )}
      </div>
    </section>
  )
}

export default ResultsDisplay
