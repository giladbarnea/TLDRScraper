import { useSupabaseStorage } from '../hooks/useSupabaseStorage'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import ArticleList from './ArticleList'
import './ResultsDisplay.css'

function enrichArticlesWithOrder(articles) {
  return articles.map((article, index) => ({
    ...article,
    originalOrder: index
  }))
}

function StatCard({ label, value }) {
  return (
    <div>
      <div className="text-sm font-medium text-slate-500 uppercase tracking-wider">
        {label}
      </div>
      <div className="text-2xl font-bold text-slate-900 mt-1">
        {value}
      </div>
    </div>
  )
}

function StatsGrid({ stats }) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-soft border border-slate-100 mb-8">
      <div className="grid grid-cols-3 gap-6">
        <StatCard label="Articles" value={stats.total_articles} />
        <StatCard label="Unique URLs" value={stats.unique_urls} />
        <StatCard label="Dates" value={`${stats.dates_with_content}/${stats.dates_processed}`} />
      </div>
    </div>
  )
}

function DateHeader({ date, loading }) {
  return (
    <div className="date-header-container" data-date={date}>
      <h2>{date}</h2>
      {loading && <span className="loading-indicator"> (loading...)</span>}
    </div>
  )
}

function IssueBlock({ date, issue, articles }) {
  const categoryArticles = articles.filter((article) => article.category === issue.category)

  return (
    <div key={`${date}-${issue.category}`} className="issue-section">
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

      <ArticleList articles={categoryArticles} />
    </div>
  )
}

function UncategorizedArticles({ articles }) {
  const uncategorized = articles.filter((article) => !article.category)

  if (uncategorized.length === 0) return null

  return <ArticleList articles={uncategorized} />
}

function ResultsDisplay({ results }) {
  return (
    <div id="result" className="result success">
      <StatsGrid stats={results.stats} />

      <main id="write">
        {(results.payloads || []).map((payload) => (
          <DailyResults key={payload.date} payload={payload} />
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
  const articles = enrichArticlesWithOrder(livePayload?.articles ?? payload.articles)
  const issues = livePayload?.issues ?? payload.issues ?? []

  return (
    <div className="date-group">
      <DateHeader date={date} loading={loading} />

      {issues.map((issue) => (
        <IssueBlock
          key={`${date}-${issue.category}`}
          date={date}
          issue={issue}
          articles={articles}
        />
      ))}

      <UncategorizedArticles articles={articles} />
    </div>
  )
}

export default ResultsDisplay
