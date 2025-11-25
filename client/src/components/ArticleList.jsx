import { useMemo } from 'react'
import ArticleCard from './ArticleCard'
import FoldableContainer from './FoldableContainer'

function ArticleList({ articles, parentId = '' }) {
  const sortedArticles = useMemo(() => {
    return [...articles].sort((a, b) => {
      const stateA = a.removed ? 1 : 0
      const stateB = b.removed ? 1 : 0

      if (stateA !== stateB) return stateA - stateB

      return (a.originalOrder ?? 0) - (b.originalOrder ?? 0)
    })
  }, [articles])

  const groupedContent = useMemo(() => {
    const groups = []
    let currentGroup = null

    sortedArticles.forEach((article, index) => {
      const sectionTitle = article.section
      const sectionEmoji = article.sectionEmoji
      const sectionKey = sectionTitle ? `${sectionEmoji || ''} ${sectionTitle}`.trim() : null

      if (sectionKey) {
        if (!currentGroup || currentGroup.type !== 'section' || currentGroup.key !== sectionKey) {
          currentGroup = { type: 'section', key: sectionKey, label: sectionKey, articles: [] }
          groups.push(currentGroup)
        }
        currentGroup.articles.push({ article, index })
      } else {
        if (!currentGroup || currentGroup.type !== 'standalone') {
          currentGroup = { type: 'standalone', articles: [] }
          groups.push(currentGroup)
        }
        currentGroup.articles.push({ article, index })
      }
    })

    return groups
  }, [sortedArticles])

  return (
    <div className="space-y-4">
      {groupedContent.map((group, groupIndex) => (
        group.type === 'section' ? (
          <FoldableContainer
            key={group.key}
            id={`${parentId}::${group.key}`}
            headerClassName="pt-6 pb-2"
            title={
              <h4 className="text-sm font-bold uppercase tracking-widest text-slate-400 ml-1">
                {group.label}
              </h4>
            }
          >
            <div className="space-y-4">
              {group.articles.map(({ article, index }) => (
                <ArticleCard key={article.url} article={article} index={index} />
              ))}
            </div>
          </FoldableContainer>
        ) : (
          <div key={`standalone-${groupIndex}`} className="space-y-4">
            {group.articles.map(({ article, index }) => (
              <ArticleCard key={article.url} article={article} index={index} />
            ))}
          </div>
        )
      ))}
    </div>
  )
}

export default ArticleList
