import { useEffect } from 'react'
import { hydrateDay, useDayArticlesSummary } from '../store/articleStore'
import FoldableContainer from './FoldableContainer'
import NewsletterDay from './NewsletterDay'
import ReadStatsBadge from './ReadStatsBadge'
import Selectable from './Selectable'

function formatDateDisplay(dateStr) {
  const dateObj = new Date(dateStr)
  const isToday = new Date().toDateString() === dateObj.toDateString()
  const niceDate = dateObj.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
  return { displayText: isToday ? 'Today' : niceDate, isToday }
}

function CalendarDayTitle({ dateStr, articleUrls }) {
  const { displayText } = formatDateDisplay(dateStr)
  return (
    <div className="flex items-center gap-2.5 py-3">
      <h2 className="font-display text-xl font-bold text-slate-900 tracking-tight">
        {displayText}
      </h2>
      <ReadStatsBadge date={dateStr} urls={articleUrls} />
    </div>
  )
}

function NewsletterList({ date, issues, articles }) {
  return (
    <div className="space-y-4">
      {issues.map(issue => {
        const newsletterName = issue.category
        const newsletterArticles = articles.filter(a => a.category === newsletterName)

        if (newsletterArticles.length === 0) return null

        return (
          <NewsletterDay
            key={`${date}-${newsletterName}`}
            date={date}
            title={newsletterName}
            issue={issue}
            articles={newsletterArticles}
          />
        )
      })}
    </div>
  )
}

function CalendarDay({ payload }) {
  // biome-ignore lint/correctness/useExhaustiveDependencies: payload is bootstrap data; hydration is keyed by date.
  useEffect(() => {
    hydrateDay(payload.date, payload)
  }, [payload.date])

  const date = payload.date
  const articles = payload.articles.map((article, index) => ({
    ...article,
    issueDate: date,
    originalOrder: index,
  }))
  const issues = payload.issues ?? []

  const { allRemoved: allArticlesRemoved } = useDayArticlesSummary(date)

  const componentId = `calendar-${date}`
  const descendantIds = articles.map(a => `article-${a.url}`)

  return (
    <Selectable id={componentId} descendantIds={descendantIds}>
      <section>
        <FoldableContainer
          id={`calendar-${date}`}
          title={<CalendarDayTitle dateStr={date} articleUrls={articles.map((article) => article.url)} />}
          defaultFolded={allArticlesRemoved}
          headerClassName="sticky top-0 z-30 bg-slate-50/95 backdrop-blur-sm border-b border-slate-200/60"
          contentClassName="mt-3"
        >
          <NewsletterList date={date} issues={issues} articles={articles} />
        </FoldableContainer>
      </section>
    </Selectable>
  )
}

export default CalendarDay
