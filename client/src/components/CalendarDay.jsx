import { motion } from 'framer-motion'
import { useDayView } from '../store/articleStore'
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

function CalendarDayTitle({ dateStr, completedCount, totalCount }) {
  const { displayText } = formatDateDisplay(dateStr)
  return (
    <div className="flex items-center gap-2.5 py-3">
      <h2 className="font-display text-xl font-bold text-slate-900 tracking-tight">
        {displayText}
      </h2>
      <ReadStatsBadge completedCount={completedCount} totalCount={totalCount} />
    </div>
  )
}

function CalendarDay({ date }) {
  const view = useDayView(date)
  if (!view) return null

  const componentId = `calendar-${date}`

  return (
    <Selectable id={componentId} descendantIds={view.articleKeys}>
      <section>
        <FoldableContainer
          id={componentId}
          title={<CalendarDayTitle dateStr={date} completedCount={view.completedCount} totalCount={view.totalCount} />}
          defaultFolded={view.allRemoved}
          headerClassName="sticky top-0 z-30 bg-slate-50/95 backdrop-blur-sm border-b border-slate-200/60"
          contentClassName="mt-3"
        >
          <div className="flex flex-col gap-4">
            {view.issues.map((issue, index) => {
              if (!issue.hasArticles) return null
              const order = issue.allRemoved ? 10_000 + index : index
              return (
                <motion.div key={`${date}-${issue.source_id}`} layout style={{ order }}>
                  <NewsletterDay date={date} sourceId={issue.source_id} />
                </motion.div>
              )
            })}
          </div>
        </FoldableContainer>
      </section>
    </Selectable>
  )
}

export default CalendarDay
