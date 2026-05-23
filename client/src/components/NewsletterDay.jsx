import { motion } from 'framer-motion'
import { useNewsletterView } from '../store/articleStore'
import ArticleList from './ArticleList'
import FoldableContainer from './FoldableContainer'
import ReadStatsBadge from './ReadStatsBadge'
import Selectable from './Selectable'

function IssueSubtitle({ subtitle, title, allRemoved }) {
  if (!subtitle || subtitle === title) return null

  return (
    <div className={`mb-3 text-xs text-slate-400 tracking-wide transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}>
      <span>{subtitle}</span>
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

function Section({ date, sourceId, section, originalOrder }) {
  const { key: sectionKey, emoji, articleKeys, allRemoved } = section
  const displayTitle = emoji ? `${emoji} ${sectionKey}` : sectionKey
  const componentId = `section-${date}-${sourceId}-${sectionKey}`
  const order = allRemoved ? 10_000 + originalOrder : originalOrder

  return (
    <motion.div layout style={{ order }}>
      <Selectable id={componentId} descendantIds={articleKeys}>
        <FoldableContainer
          id={componentId}
          title={<SectionTitle displayTitle={displayTitle} />}
          headerClassName="transition-all duration-300"
          defaultFolded={allRemoved}
          className={`transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}
        >
          <div className="mt-2 transition-all duration-300">
            <ArticleList articleKeys={articleKeys} />
          </div>
        </FoldableContainer>
      </Selectable>
    </motion.div>
  )
}

function NewsletterDay({ date, sourceId }) {
  const view = useNewsletterView(date, sourceId)
  if (!view) return null

  const { title, issue, articleKeys, sections, hasSections, allRemoved, completedCount, totalCount } = view
  const componentId = `newsletter-${date}-${sourceId}`

  return (
    <Selectable id={componentId} descendantIds={articleKeys}>
      <FoldableContainer
        id={componentId}
        headerClassName="border-b border-slate-100 transition-all duration-300"
        className={`transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}
        dataAttributes={{
          'data-testid': 'newsletter-day',
          'data-source-id': sourceId,
          'data-date': date,
        }}
        title={
          <div className="flex items-center gap-2.5 py-2">
            <h3 className="font-display font-semibold text-[17px] text-slate-900">
              {title}
            </h3>
            <ReadStatsBadge completedCount={completedCount} totalCount={totalCount} />
          </div>
        }
        defaultFolded={allRemoved}
      >
        <div className="mt-3 flex flex-col gap-3">
          <IssueSubtitle subtitle={issue?.subtitle} title={title} allRemoved={allRemoved} />

          {hasSections ? (
            sections.map((section, index) => (
              <Section
                key={`${title}-${section.key}`}
                date={date}
                sourceId={sourceId}
                section={section}
                originalOrder={index}
              />
            ))
          ) : (
            <ArticleList articleKeys={articleKeys} />
          )}
        </div>
      </FoldableContainer>
    </Selectable>
  )
}

export default NewsletterDay
