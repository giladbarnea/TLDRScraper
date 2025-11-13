import { useMemo } from 'react'
import { useArticleState } from '../hooks/useArticleState'
import { useSummary } from '../hooks/useSummary'
import './ArticleCard.css'

function ArticleCard({ article, index }) {
  const { isRead, isRemoved, isTldrHidden, toggleRead, toggleRemove, markTldrHidden, unmarkTldrHidden, loading: stateLoading } = useArticleState(
    article.issueDate,
    article.url
  )

  const tldr = useSummary(article.issueDate, article.url, 'tldr')

  const cardClasses = [
    'article-card',
    !isRead && 'unread',
    isRead && 'read',
    isRemoved && 'removed',
    isTldrHidden && 'tldr-hidden'
  ].filter(Boolean).join(' ')

  const fullUrl = useMemo(() => {
    const url = article.url
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url
    }
    return `https://${url}`
  }, [article.url])

  const faviconUrl = useMemo(() => {
    try {
      const url = new URL(fullUrl)
      return `${url.origin}/favicon.ico`
    } catch {
      return null
    }
  }, [fullUrl])

  const handleLinkClick = (e) => {
    if (isRemoved) return
    if (e.ctrlKey || e.metaKey) return

    if (!isRead) {
      toggleRead()
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
            href={fullUrl}
            className={`article-link ${stateLoading ? 'loading' : ''}`}
            target="_blank"
            rel="noopener noreferrer"
            data-url={fullUrl}
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
          <button
            className={`article-btn tldr-btn ${tldr.isAvailable ? 'loaded' : ''} ${tldr.expanded ? 'expanded' : ''}`}
            disabled={stateLoading || tldr.loading}
            type="button"
            title={tldr.isAvailable ? 'TLDR cached - click to show' : 'Show TLDR'}
            onClick={handleTldrClick}
          >
            {tldr.buttonLabel}
          </button>

          <button
            className="article-btn remove-article-btn"
            type="button"
            title={isRemoved ? 'Restore this article to the list' : 'Remove this article from the list'}
            disabled={stateLoading}
            onClick={toggleRemove}
          >
            {isRemoved ? 'Restore' : 'Remove'}
          </button>
        </div>
      </div>

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
