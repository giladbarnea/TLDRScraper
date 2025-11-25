import ArticleList from './ArticleList'
import FoldableContainer from './FoldableContainer'

function NewsletterDay({ title, articles }) {
  // Group articles by section (Category)
  // We use the 'section' property of articles to group them.
  // If an article has no section, it goes into "Other" or stays at top level?
  // User wants "real categories" to be foldable.
  
  const sections = articles.reduce((acc, article) => {
    const sectionKey = article.section || 'Other'
    if (!acc[sectionKey]) {
      acc[sectionKey] = []
    }
    acc[sectionKey].push(article)
    return acc
  }, {})

  // We need to maintain the order of sections. 
  // Ideally we should use the order from the first article of that section or `sectionOrder` if available.
  const sortedSections = Object.keys(sections).sort((a, b) => {
    if (a === 'Other') return 1
    if (b === 'Other') return -1
    
    const articleA = sections[a][0]
    const articleB = sections[b][0]
    
    return (articleA.sectionOrder ?? 0) - (articleB.sectionOrder ?? 0)
  })

  return (
    <FoldableContainer 
      id={`newsletter-${title}`}
      title={
        <h3 className="font-display font-bold text-xl text-slate-800 py-2">
          {title}
        </h3>
      }
      className="mb-4"
    >
      <div className="pl-4 space-y-6 mt-2 border-l-2 border-slate-100 ml-2">
        {sortedSections.map((sectionKey) => {
          const sectionArticles = sections[sectionKey]
          const allRemoved = sectionArticles.every(a => a.removed)
          
          // If section is "Other" and it's the only section, maybe we don't need a folder?
          // But consistency is good.
          
          const firstArticle = sectionArticles[0]
          const sectionEmoji = firstArticle.sectionEmoji
          const displayTitle = sectionEmoji ? `${sectionEmoji} ${sectionKey}` : sectionKey

          const SectionTitle = (
             <div className={`flex items-center gap-3 transition-all duration-300`}>
               <h4 className={`font-display font-bold text-lg transition-all duration-300 ${allRemoved ? 'text-slate-400 line-through decoration-2' : 'text-slate-700'}`}>
                 {displayTitle}
               </h4>
             </div>
          )

          return (
            <FoldableContainer 
              key={`${title}-${sectionKey}`}
              id={`section-${title}-${sectionKey}`}
              title={SectionTitle}
              className="mb-4"
            >
               <div className="space-y-4 mt-2">
                  <ArticleList 
                    articles={sectionArticles} 
                    showSectionHeaders={false} 
                  />
               </div>
            </FoldableContainer>
          )
        })}
      </div>
    </FoldableContainer>
  )
}

export default NewsletterDay
