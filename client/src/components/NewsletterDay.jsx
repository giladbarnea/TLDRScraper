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
    <div className={`mb-3 text-xs text-slate-400 tracking-wide transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}>
      <span>{issue.subtitle}</span>
    </div>
  )
}

function SectionTitle({ displayTitle }) {
  return (
    <div className="flex items-center gap-2">
      <h4 className="font-semibold text-xs uppercase tracking-wider text-slate-400">
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
  const descendantIds = articles.map(a => `article-${a.url}`)

  return (
    <Selectable id={componentId} descendantIds={descendantIds}>
      <FoldableContainer
        key={`${newsletterTitle}-${sectionKey}`}
        id={componentId}
        title={<SectionTitle displayTitle={displayTitle} />}
        headerClassName={`transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}
        defaultFolded={allRemoved}
        className="mb-3"
      >
        <div className={`mt-2 transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}>
          <ArticleList articles={articles} showSectionHeaders={false} />
        </div>
      </FoldableContainer>
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

  const componentId = `newsletter-${date}-${issue.source_id}`
  const descendantIds = articles.map(a => `article-${a.url}`)

  return (
    <Selectable id={componentId} descendantIds={descendantIds}>
      <FoldableContainer
        id={componentId}
        headerClassName={`border-b border-slate-100 transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}
        title={
          <div className="flex items-center gap-2.5 py-2">
            <h3 className="font-display font-semibold text-[17px] text-slate-900">
              {title}
            </h3>
            <ReadStatsBadge articles={articles} />
          </div>
        }
        defaultFolded={allRemoved}
      >
        <div className="space-y-4 mt-3">
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
    </Selectable>
  )
}

export default NewsletterDay
