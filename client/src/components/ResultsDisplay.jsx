import { useSupabaseStorage } from '../hooks/useSupabaseStorage'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import ArticleList from './ArticleList'
import './ResultsDisplay.css'

function ResultsDisplay({ results }) {
  return (
    <div id="result" className="result success">
      {/* Prominent Stats Section */}
      <div className="bg-white rounded-2xl p-6 shadow-soft border border-slate-100 mb-8">
        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className="text-sm font-medium text-slate-500 uppercase tracking-wider">
              Articles
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {results.stats.total_articles}
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-500 uppercase tracking-wider">
              Unique URLs
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {results.stats.unique_urls}
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-500 uppercase tracking-wider">
              Dates
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {results.stats.dates_with_content}/{results.stats.dates_processed}
            </div>
          </div>
        </div>
      </div>

      <main id="write">
        {(results.payloads || []).map((payload) => (
          <DailyResults
            key={payload.date}
            payload={payload}
          />
        ))}
      </main>
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

  return (
    <div className="date-group">
      <div className="date-header-container" data-date={date}>
        <h2>{date}</h2>
        {loading && <span className="loading-indicator"> (loading...)</span>}
      </div>

      {issues.map((issue) => (
        <div
          key={`${date}-${issue.category}`}
          className="issue-section"
        >
          <div className="issue-header-container">
            <h4>{issue.category}</h4>
          </div>

          {(issue.title || issue.subtitle) && (
            <div className="issue-title-block">
              {issue.title && (
                <div className="issue-title-line">{issue.title}</div>
              )}
              {issue.subtitle && issue.subtitle !== issue.title && (
                <div className="issue-title-line">{issue.subtitle}</div>
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
  )
}

export default ResultsDisplay
