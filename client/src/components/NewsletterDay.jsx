import ArticleList from './ArticleList'
import FoldableContainer from './FoldableContainer'

function NewsletterDay({ date, title, issue, articles }) {
  const allRemoved = articles.length > 0 && articles.every(a => a.removed)
  const hasSections = articles.some(a => a.section)

  const sections = hasSections ? articles.reduce((acc, article) => {
    const sectionKey = article.section
    if (!acc[sectionKey]) {
      acc[sectionKey] = []
    }
    acc[sectionKey].push(article)
    return acc
  }, {}) : {}

  const sortedSections = hasSections ? Object.keys(sections).sort((a, b) => {
    const articleA = sections[a][0]
    const articleB = sections[b][0]
    return (articleA.sectionOrder ?? 0) - (articleB.sectionOrder ?? 0)
  }) : []

  return (
    <FoldableContainer
      id={`newsletter-${date}-${title}`}
      headerClassName={`pl-1 border-l-2 transition-all duration-300 ${allRemoved ? 'border-slate-200 opacity-50' : 'border-brand-200'}`}
      title={
        <h3 className="font-display font-bold text-xl py-2 text-slate-800">
          {title}
        </h3>
      }
      defaultFolded={allRemoved}
      className="mb-8"
    >
      <div className="pl-4 space-y-6 mt-2 border-l-2 border-slate-100 ml-2">
        {/* Issue Title & Subtitle Display */}
        {issue && (issue.title || issue.subtitle) && (
          <div className={`p-4 rounded-xl border mb-6 transition-all duration-300 ${allRemoved ? 'bg-slate-50 border-slate-200 opacity-50' : 'bg-white border-slate-100 shadow-sm'}`}>
            {issue.title && <div className="font-semibold text-lg text-slate-900">{issue.title}</div>}
            {issue.subtitle && issue.subtitle !== issue.title && (
              <div className="text-sm mt-1 text-slate-500">{issue.subtitle}</div>
            )}
          </div>
        )}

        {hasSections ? (
          sortedSections.map((sectionKey) => {
            const sectionArticles = sections[sectionKey]
            const sectionAllRemoved = sectionArticles.every(a => a.removed)
            
            const firstArticle = sectionArticles[0]
            const sectionEmoji = firstArticle.sectionEmoji
            const displayTitle = sectionEmoji ? `${sectionEmoji} ${sectionKey}` : sectionKey

            const SectionTitle = (
               <div className="flex items-center gap-3">
                 <h4 className="font-display font-bold text-lg text-slate-700">
                   {displayTitle}
                 </h4>
               </div>
            )

            return (
              <FoldableContainer
                key={`${title}-${sectionKey}`}
                id={`section-${date}-${title}-${sectionKey}`}
                title={SectionTitle}
                headerClassName={`transition-all duration-300 ${sectionAllRemoved ? 'opacity-50' : ''}`}
                defaultFolded={sectionAllRemoved}
                className="mb-4"
              >
                 <div className={`space-y-4 mt-2 transition-all duration-300 ${sectionAllRemoved ? 'opacity-50' : ''}`}>
                    <ArticleList 
                      articles={sectionArticles} 
                      showSectionHeaders={false} 
                    />
                 </div>
              </FoldableContainer>
            )
          })
        ) : (
          <ArticleList articles={articles} showSectionHeaders={false} />
        )}
      </div>
    </FoldableContainer>
  )
}

export default NewsletterDay
