import { useState } from 'react'
import { createPortal } from 'react-dom'
import { useLocalStorage } from '../hooks/useLocalStorage'
import ArticleList from './ArticleList'
import './ResultsDisplay.css'

function ResultsDisplay({ results }) {
  const [showToast, setShowToast] = useState(false)

  const statsLines = [
    `📊 Stats: ${results.stats.total_articles} articles, ${results.stats.unique_urls} unique URLs`,
    `📅 Dates: ${results.stats.dates_with_content}/${results.stats.dates_processed} with content`,
    results.source && `Source: ${results.source}`
  ].filter(Boolean)

  const debugLogs = results.debugLogs || []

  const handleCopySummary = () => {
    setShowToast(true)
    setTimeout(() => setShowToast(false), 2000)
  }

  return (
    <div id="result" className="result success">
      <div className="stats">
        {statsLines.map((line, index) => (
          <div key={index}>{line}</div>
        ))}
      </div>

      {debugLogs.length > 0 && (
        <div id="logs-slot" className="logs-slot">
          <details>
            <summary>Debug logs</summary>
            <pre>{debugLogs.join('\n')}</pre>
          </details>
        </div>
      )}

      <main id="write">
        {(results.payloads || []).map((payload) => (
          <DailyResults
            key={payload.date}
            payload={payload}
            onCopySummary={handleCopySummary}
          />
        ))}
      </main>

      {createPortal(
        <div id="copyToast" className={`copy-toast ${showToast ? 'show' : ''}`}>
          Copied to clipboard
        </div>,
        document.body
      )}
    </div>
  )
}

function DailyResults({ payload, onCopySummary }) {
  const [livePayload] = useLocalStorage(
    `newsletters:scrapes:${payload.date}`,
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
            onCopySummary={onCopySummary}
          />
        </div>
      ))}

      {articles.some((article) => !article.category) && (
        <ArticleList
          articles={articles.filter((article) => !article.category)}
          onCopySummary={onCopySummary}
        />
      )}
    </div>
  )
}

export default ResultsDisplay
