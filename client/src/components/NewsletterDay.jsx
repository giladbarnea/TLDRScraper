import ArticleList from './ArticleList'
import FoldableContainer from './FoldableContainer'
import ReadStatsBadge from './ReadStatsBadge'
import Selectable from './Selectable'

function groupArticlesBySection(articles) {
  return articles.reduce((acc, article) => {
    const sectionKey = article.section
    if (!acc[sectionKey]) {
      acc[sectionKey] = []
    }
    acc[sectionKey].push(article)
    return acc
  }, {})
}

function getSortedSectionKeys(sections) {
  return Object.keys(sections).sort((a, b) => {
    const articleA = sections[a][0]
    const articleB = sections[b][0]
    return (articleA.sectionOrder ?? 0) - (articleB.sectionOrder ?? 0)
  })
}

function IssueSubtitle({ issue, allRemoved }) {
  if (!issue?.subtitle || issue.subtitle === issue.title) return null

  return (
    <div className={`mb-6 text-xs text-slate-400 tracking-wide transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}>
      <span>{issue.subtitle}</span>
    </div>
  )
}

function SectionTitle({ displayTitle }) {
  return (
    <div className="flex items-center gap-3">
      <h4 className="font-display font-bold text-lg text-slate-700">
        {displayTitle}
      </h4>
    </div>
  )
}

function Section({ date, sourceId, newsletterTitle, sectionKey, articles }) {
  const allRemoved = articles.every(a => a.removed)
  const sectionEmoji = articles[0].sectionEmoji
  const displayTitle = sectionEmoji ? `${sectionEmoji} ${sectionKey}` : sectionKey
  const componentId = `section-${date}-${sourceId}-${sectionKey}`

  return (
    <Selectable id={componentId} title={displayTitle}>
      {({ menuButton }) => (
        <FoldableContainer
          key={`${newsletterTitle}-${sectionKey}`}
          id={`section-${date}-${newsletterTitle}-${sectionKey}`}
          title={<SectionTitle displayTitle={displayTitle} />}
          headerClassName={`transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}
          defaultFolded={allRemoved}
          className="mb-4"
          rightContent={menuButton}
        >
          <div className={`space-y-4 mt-2 transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}>
            <ArticleList articles={articles} showSectionHeaders={false} />
          </div>
        </FoldableContainer>
      )}
    </Selectable>
  )
}

function SectionsList({ date, sourceId, title, sections, sortedSectionKeys }) {
  return sortedSectionKeys.map(sectionKey => (
    <Section
      key={`${title}-${sectionKey}`}
      date={date}
      sourceId={sourceId}
      newsletterTitle={title}
      sectionKey={sectionKey}
      articles={sections[sectionKey]}
    />
  ))
}

function NewsletterDay({ date, title, issue, articles }) {
  const allRemoved = articles.length > 0 && articles.every(a => a.removed)
  const hasSections = articles.some(a => a.section)

  const sections = hasSections ? groupArticlesBySection(articles) : {}
  const sortedSectionKeys = hasSections ? getSortedSectionKeys(sections) : []

  // Use unified ID that's stable across frontend and backend.
  // For newsletter issues, we use (date, source_id) which matches the backend's
  // composite key design. We use issue.source_id (e.g., "tldr_tech") NOT title/category
  // (e.g., "TLDR Tech") because source_id is the canonical, stable identifier.
  const componentId = `newsletter-${date}-${issue.source_id}`

  return (
    <Selectable id={componentId} title={title}>
      {({ menuButton }) => (
        <FoldableContainer
          id={`newsletter-${date}-${title}`}
          headerClassName={`transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}
          title={
            <div className="flex items-center gap-3 py-2">
              <h3 className="font-display font-bold text-xl text-slate-800">
                {title}
              </h3>
              <ReadStatsBadge articles={articles} />
            </div>
          }
          defaultFolded={allRemoved}
          className="mb-8"
          rightContent={menuButton}
        >
          <div className="space-y-6 mt-4">
            <IssueSubtitle issue={issue} allRemoved={allRemoved} />

            {hasSections ? (
              <SectionsList
                date={date}
                sourceId={issue.source_id}
                title={title}
                sections={sections}
                sortedSectionKeys={sortedSectionKeys}
              />
            ) : (
              <ArticleList articles={articles} showSectionHeaders={false} />
            )}
          </div>
        </FoldableContainer>
      )}
    </Selectable>
  )
}

export default NewsletterDay
