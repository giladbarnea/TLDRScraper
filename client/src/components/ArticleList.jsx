import ArticleCard from './ArticleCard'

function ArticleList({ articles, showSectionHeaders = true }) {
  const sortedArticles = [...articles].sort((a, b) => {
    const stateA = a.removed ? 1 : 0
    const stateB = b.removed ? 1 : 0

    if (stateA !== stateB) return stateA - stateB

    return (a.originalOrder ?? 0) - (b.originalOrder ?? 0)
  })

  const sectionsWithArticles = (() => {
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
  })()

  return (
    <div>
      {sectionsWithArticles.map((item) => (
        item.type === 'section' ? (
          showSectionHeaders && (
            <div key={item.key} className="pt-4 pb-1">
              <h4 className="font-semibold text-xs uppercase tracking-wider text-slate-400 ml-1">
                {item.label}
              </h4>
            </div>
          )
        ) : (
          <ArticleCard
            key={item.key}
            article={item.article}
          />
        )
      ))}
    </div>
  )
}

export default ArticleList
