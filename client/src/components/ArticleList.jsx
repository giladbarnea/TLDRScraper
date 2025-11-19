import { useMemo } from 'react'
import ArticleCard from './ArticleCard'

function ArticleList({ articles }) {
  const sortedArticles = useMemo(() => {
    return [...articles].sort((a, b) => {
      const stateA = a.removed ? 3
        : a.tldrHidden ? 2
        : a.read?.isRead ? 1
        : 0
      const stateB = b.removed ? 3
        : b.tldrHidden ? 2
        : b.read?.isRead ? 1
        : 0

      if (stateA !== stateB) return stateA - stateB

      return (a.originalOrder ?? 0) - (b.originalOrder ?? 0)
    })
  }, [articles])

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
    <div className="space-y-2">
      {sectionsWithArticles.map((item) => (
        item.type === 'section' ? (
          <div key={item.key} className="pt-6 pb-3 flex items-center gap-3 justify-center opacity-80">
            <div className="h-px bg-slate-200 w-8"></div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
              {item.label}
            </span>
            <div className="h-px bg-slate-200 w-8"></div>
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
