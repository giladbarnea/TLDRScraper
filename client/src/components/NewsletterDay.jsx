import { useState } from 'react'
import ArticleList from './ArticleList'
import BottomSheet from './BottomSheet'
import FoldableContainer from './FoldableContainer'
import ReadStatsBadge from './ReadStatsBadge'
import ThreeDotMenuButton from './ThreeDotMenuButton'

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

function SectionTitle({ sectionKey, sectionEmoji }) {
  const displayTitle = sectionEmoji ? `${sectionEmoji} ${sectionKey}` : sectionKey
  return (
    <div className="flex items-center gap-3">
      <h4 className="font-display font-bold text-lg text-slate-700">
        {displayTitle}
      </h4>
    </div>
  )
}

function Section({ date, newsletterTitle, sectionKey, articles }) {
  const allRemoved = articles.every(a => a.removed)
  const sectionEmoji = articles[0].sectionEmoji

  return (
    <FoldableContainer
      key={`${newsletterTitle}-${sectionKey}`}
      id={`section-${date}-${newsletterTitle}-${sectionKey}`}
      title={<SectionTitle sectionKey={sectionKey} sectionEmoji={sectionEmoji} />}
      headerClassName={`transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}
      defaultFolded={allRemoved}
      className="mb-4"
    >
      <div className={`space-y-4 mt-2 transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}>
        <ArticleList articles={articles} showSectionHeaders={false} />
      </div>
    </FoldableContainer>
  )
}

function SectionsList({ date, title, sections, sortedSectionKeys }) {
  return sortedSectionKeys.map(sectionKey => (
    <Section
      key={`${title}-${sectionKey}`}
      date={date}
      newsletterTitle={title}
      sectionKey={sectionKey}
      articles={sections[sectionKey]}
    />
  ))
}

function NewsletterDay({ date, title, issue, articles }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const allRemoved = articles.length > 0 && articles.every(a => a.removed)
  const hasSections = articles.some(a => a.section)

  const sections = hasSections ? groupArticlesBySection(articles) : {}
  const sortedSectionKeys = hasSections ? getSortedSectionKeys(sections) : []

  const handleSelect = () => {
    const storageKey = 'podcastSources-1'
    const existing = JSON.parse(localStorage.getItem(storageKey) || '[]')
    const componentId = `newsletter-${date}-${title}`
    if (!existing.includes(componentId)) {
      existing.push(componentId)
      localStorage.setItem(storageKey, JSON.stringify(existing))
    }
    setMenuOpen(false)
  }

  return (
    <>
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
        rightContent={<ThreeDotMenuButton onClick={() => setMenuOpen(true)} />}
      >
        <div className="space-y-6 mt-4">
          <IssueSubtitle issue={issue} allRemoved={allRemoved} />

          {hasSections ? (
            <SectionsList
              date={date}
              title={title}
              sections={sections}
              sortedSectionKeys={sortedSectionKeys}
            />
          ) : (
            <ArticleList articles={articles} showSectionHeaders={false} />
          )}
        </div>
      </FoldableContainer>

      <BottomSheet
        isOpen={menuOpen}
        onClose={() => setMenuOpen(false)}
        title={title}
      >
        <button
          onClick={handleSelect}
          className="w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 rounded-xl text-slate-700 font-medium transition-colors"
        >
          Select
        </button>
      </BottomSheet>
    </>
  )
}

export default NewsletterDay
