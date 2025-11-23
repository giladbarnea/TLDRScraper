import { useSupabaseStorage } from '../hooks/useSupabaseStorage'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import ArticleList from './ArticleList'

function Feed({ payloads }) {
  return (
    <div className="space-y-16 pb-32">
      {payloads.map((payload) => (
        <DailyGroup key={payload.date} payload={payload} />
      ))}
    </div>
  )
}

function DailyGroup({ payload }) {
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
  const niceDate = dateObj.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
  const isToday = new Date().toDateString() === dateObj.toDateString()

  return (
    <section className="animate-slide-up">
      <div className="sticky top-20 z-30 bg-slate-50/95 backdrop-blur-sm py-4 mb-6 border-b border-slate-200/60">
        <div className="flex items-baseline gap-3">
          <h2 className="font-display text-2xl font-bold text-slate-900 tracking-tight">
            {isToday ? 'Today' : niceDate}
          </h2>
          {loading && <span className="text-xs font-medium text-brand-500 animate-pulse">Syncing...</span>}
        </div>
      </div>

      <div className="space-y-12">
        {issues.map((issue) => {
          const categoryArticles = articles.filter((article) => article.category === issue.category)
          const allRemoved = categoryArticles.length > 0 && categoryArticles.every((article) => article.removed)

          return (
            <div key={`${date}-${issue.category}`} className="space-y-6">
              <div className={`flex items-center gap-3 pl-1 border-l-2 transition-all duration-300 ${allRemoved ? 'border-slate-200 opacity-50' : 'border-brand-200'}`}>
                <h3 className={`font-display font-bold text-lg pl-3 transition-all duration-300 ${allRemoved ? 'text-slate-400 line-through decoration-2' : 'text-slate-800'}`}>
                  {issue.category}
                </h3>
              </div>

              {(issue.title || issue.subtitle) && (
                <div className={`p-4 rounded-xl border mx-1 transition-all duration-300 ${allRemoved ? 'bg-slate-50 border-slate-200 opacity-50' : 'bg-white border-slate-100 shadow-sm'}`}>
                  {issue.title && <div className={`font-semibold transition-all duration-300 ${allRemoved ? 'text-slate-400 line-through decoration-2' : 'text-slate-900'}`}>{issue.title}</div>}
                  {issue.subtitle && issue.subtitle !== issue.title && (
                    <div className={`text-sm mt-1 transition-all duration-300 ${allRemoved ? 'text-slate-300 line-through decoration-2' : 'text-slate-500'}`}>{issue.subtitle}</div>
                  )}
                </div>
              )}

              <ArticleList
                articles={categoryArticles}
              />
            </div>
          )
        })}

        {articles.some((article) => !article.category) && (
           <div className="space-y-6">
              <div className="pl-4 border-l-2 border-slate-200">
                 <h3 className="font-display font-bold text-lg text-slate-400">Other</h3>
              </div>
              <ArticleList articles={articles.filter((article) => !article.category)} />
           </div>
        )}
      </div>
    </section>
  )
}

export default Feed
