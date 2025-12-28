import { useSupabaseStorage } from '../hooks/useSupabaseStorage'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import FoldableContainer from './FoldableContainer'
import NewsletterDay from './NewsletterDay'
import ReadStatsBadge from './ReadStatsBadge'

function formatDateDisplay(dateStr) {
  const dateObj = new Date(dateStr)
  const isToday = new Date().toDateString() === dateObj.toDateString()
  const niceDate = dateObj.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
  return { displayText: isToday ? 'Today' : niceDate, isToday }
}

function CalendarDayTitle({ dateStr, loading, articles }) {
  const { displayText } = formatDateDisplay(dateStr)
  return (
    <div className="flex items-center gap-3 py-4">
      <h2 className="font-display text-2xl font-bold text-slate-900 tracking-tight">
        {displayText}
      </h2>
      <ReadStatsBadge articles={articles} />
      {loading && <span className="text-xs font-medium text-brand-500 animate-pulse">Syncing...</span>}
    </div>
  )
}

function NewsletterList({ date, issues, articles }) {
  return (
    <div className="space-y-8">
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
  const [livePayload, , , { loading }] = useSupabaseStorage(
    getNewsletterScrapeKey(payload.date),
    payload
  )

  const date = livePayload?.date ?? payload.date
  const articles = (livePayload?.articles ?? payload.articles).map((article, index) => ({
    ...article,
    originalOrder: index
  }))
  const issues = livePayload?.issues ?? payload.issues ?? []

  const allArticlesRemoved = articles.length > 0 && articles.every(a => a.removed)

  return (
    <section className="animate-slide-up mb-12">
      <FoldableContainer
        id={`calendar-${date}`}
        title={<CalendarDayTitle dateStr={date} loading={loading} articles={articles} />}
        defaultFolded={allArticlesRemoved}
        headerClassName="sticky top-0 z-30 bg-slate-50/95 backdrop-blur-sm border-b border-slate-200/60"
        contentClassName="mt-4"
      >
        <NewsletterList date={date} issues={issues} articles={articles} />
      </FoldableContainer>
    </section>
  )
}

export default CalendarDay
