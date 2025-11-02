import { useMemo } from 'react'
import { useArticleState } from '../hooks/useArticleState'
import { useSummary } from '../hooks/useSummary'
import './ArticleCard.css'

function ArticleCard({ article, index, onCopySummary }) {
  const { isRead, isRemoved, isTldrHidden, toggleRead, toggleRemove, markTldrHidden, unmarkTldrHidden } = useArticleState(
    article.issueDate,
    article.url
  )

  const summary = useSummary(article.issueDate, article.url, 'summary')
  const tldr = useSummary(article.issueDate, article.url, 'tldr')

  const cardClasses = [
    'article-card',
    !isRead && 'unread',
    isRead && 'read',
    isRemoved && 'removed',
    isTldrHidden && 'tldr-hidden'
  ].filter(Boolean).join(' ')

  const faviconUrl = useMemo(() => {
    try {
      const url = new URL(article.url)
      return `${url.origin}/favicon.ico`
    } catch {
      return null
    }
  }, [article.url])

  const handleLinkClick = (e) => {
    if (isRemoved) return
    if (e.ctrlKey || e.metaKey) return

    e.preventDefault()
    summary.toggle()
    if (!isRead) {
      toggleRead()
    }
  }

  const copyToClipboard = async () => {
    const text = `---
title: ${article.title}
url: ${article.url}
---
${summary.markdown}`

    try {
      await navigator.clipboard.writeText(text)
      onCopySummary()
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleTldrClick = () => {
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

  return (
    <div className={cardClasses} data-original-order={index}>
      <div className="article-header">
        <div className="article-number">{index + 1}</div>

        <div className="article-content">
          <a
            href={article.url}
            className="article-link"
            target="_blank"
            rel="noopener noreferrer"
            data-url={article.url}
            tabIndex={isRemoved ? -1 : 0}
            onClick={handleLinkClick}
          >
            {faviconUrl && (
              <img
                src={faviconUrl}
                className="article-favicon"
                loading="lazy"
                alt=""
                onError={(e) => e.target.style.display = 'none'}
              />
            )}
            <span className="article-link-text">{article.title}</span>
          </a>
        </div>

        <div className="article-actions">
          <div className="expand-btn-container">
            <button
              className={`article-btn expand-btn ${summary.isAvailable ? 'loaded' : ''} ${summary.expanded ? 'expanded' : ''}`}
              disabled={summary.loading}
              type="button"
              title={summary.isAvailable ? 'Summary cached - click to show' : 'Show summary with default reasoning effort'}
              onClick={() => summary.toggle()}
            >
              {summary.buttonLabel}
            </button>

            <button
              className="article-btn expand-chevron-btn"
              type="button"
              title="Choose reasoning effort level"
            >
              ▾
            </button>
          </div>

          <button
            className={`article-btn tldr-btn ${tldr.isAvailable ? 'loaded' : ''} ${tldr.expanded ? 'expanded' : ''}`}
            disabled={tldr.loading}
            type="button"
            title={tldr.isAvailable ? 'TLDR cached - click to show' : 'Show TLDR'}
            onClick={handleTldrClick}
          >
            {tldr.buttonLabel}
          </button>

          {summary.isAvailable && (
            <button
              className="article-btn copy-summary-btn visible"
              type="button"
              title="Copy summary"
              onClick={copyToClipboard}
            >
              <svg
                aria-hidden="true"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
            </button>
          )}

          <button
            className="article-btn remove-article-btn"
            type="button"
            title={isRemoved ? 'Restore this article to the list' : 'Remove this article from the list'}
            onClick={toggleRemove}
          >
            {isRemoved ? 'Restore' : 'Remove'}
          </button>
        </div>
      </div>

      {summary.expanded && summary.html && (
        <div className="inline-summary">
          <strong>Summary</strong>
          <div dangerouslySetInnerHTML={{ __html: summary.html }} />
        </div>
      )}

      {tldr.expanded && tldr.html && (
        <div className="inline-tldr">
          <strong>TLDR</strong>
          <div dangerouslySetInnerHTML={{ __html: tldr.html }} />
        </div>
      )}
    </div>
  )
}

export default ArticleCard
