import { useMemo, useState, useEffect } from 'react'
import ArticleCard from './ArticleCard'
import * as storageApi from '../lib/storageApi'
import './ArticleList.css'

function ArticleList({ articles }) {
  const [storageVersion, setStorageVersion] = useState(0)
  const [articleStates, setArticleStates] = useState({})

  useEffect(() => {
    const handleStorageChange = () => {
      setStorageVersion(v => v + 1)
    }

    window.addEventListener('supabase-storage-change', handleStorageChange)
    return () => window.removeEventListener('supabase-storage-change', handleStorageChange)
  }, [])

  useEffect(() => {
    async function loadStates() {
      const states = {}

      for (const article of articles) {
        const payload = await storageApi.getDailyPayload(article.issueDate)
        if (payload) {
          const liveArticle = payload.articles?.find(a => a.url === article.url)
          if (liveArticle) {
            if (liveArticle.removed) states[article.url] = 3
            else if (liveArticle.tldrHidden) states[article.url] = 2
            else if (liveArticle.read?.isRead) states[article.url] = 1
            else states[article.url] = 0
          } else {
            if (article.removed) states[article.url] = 3
            else if (article.tldrHidden) states[article.url] = 2
            else if (article.read?.isRead) states[article.url] = 1
            else states[article.url] = 0
          }
        } else {
          if (article.removed) states[article.url] = 3
          else if (article.tldrHidden) states[article.url] = 2
          else if (article.read?.isRead) states[article.url] = 1
          else states[article.url] = 0
        }
      }

      setArticleStates(states)
    }

    loadStates()
  }, [articles, storageVersion])

  const sortedArticles = useMemo(() => {
    return [...articles].sort((a, b) => {
      const stateA = articleStates[a.url] ?? 0
      const stateB = articleStates[b.url] ?? 0

      if (stateA !== stateB) return stateA - stateB

      return (a.originalOrder ?? 0) - (b.originalOrder ?? 0)
    })
  }, [articles, articleStates])

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
