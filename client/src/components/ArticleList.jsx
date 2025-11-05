import { useMemo, useState, useEffect } from 'react'
import ArticleCard from './ArticleCard'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import './ArticleList.css'

function ArticleList({ articles }) {
  const [storageVersion, setStorageVersion] = useState(0)

  useEffect(() => {
    const handleStorageChange = () => {
      setStorageVersion(v => v + 1)
    }

    window.addEventListener('local-storage-change', handleStorageChange)
    return () => window.removeEventListener('local-storage-change', handleStorageChange)
  }, [])

  const getArticleState = (article) => {
    const storageKey = getNewsletterScrapeKey(article.issueDate)
    try {
      const raw = localStorage.getItem(storageKey)
      if (raw) {
        const payload = JSON.parse(raw)
        const liveArticle = payload.articles?.find(a => a.url === article.url)
        if (liveArticle) {
          if (liveArticle.removed) return 3
          if (liveArticle.tldrHidden) return 2
          if (liveArticle.read?.isRead) return 1
          return 0
        }
      }
    } catch (err) {
      console.error('Failed to read from localStorage:', err)
    }

    if (article.removed) return 3
    if (article.tldrHidden) return 2
    if (article.read?.isRead) return 1
    return 0
  }

  const sortedArticles = useMemo(() => {
    storageVersion
    return [...articles].sort((a, b) => {
      const stateDiff = getArticleState(a) - getArticleState(b)
      if (stateDiff !== 0) return stateDiff

      const orderA = a.originalOrder ?? 0
      const orderB = b.originalOrder ?? 0
      return orderA - orderB
    })
  }, [articles, storageVersion])

  const sectionsWithArticles = useMemo(() => {
    const sections = []
    let currentSection = null

    sortedArticles.forEach((article, index) => {
      const sectionTitle = article.section
      const sectionEmoji = article.sectionEmoji
      const sectionKey = sectionTitle ? `${sectionEmoji || ''} ${sectionTitle}`.trim() : null

      if (sectionKey && sectionKey !== currentSection) {
        sections.push({
          type: 'section',
          key: sectionKey,
          label: sectionKey
        })
        currentSection = sectionKey
      } else if (!sectionTitle && currentSection !== null) {
        currentSection = null
      }

      sections.push({
        type: 'article',
        key: article.url,
        article,
        index
      })
    })

    return sections
  }, [sortedArticles])

  return (
    <div className="article-list">
      {sectionsWithArticles.map((item) => (
        item.type === 'section' ? (
          <div key={item.key} className="section-title">
            {item.label}
          </div>
        ) : (
          <ArticleCard
            key={item.key}
            article={item.article}
            index={item.index}
          />
        )
      ))}
    </div>
  )
}

export default ArticleList
