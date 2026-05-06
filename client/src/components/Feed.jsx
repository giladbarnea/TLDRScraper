import { useVisibleDates } from '../store/articleStore'
import CalendarDay from './CalendarDay'

function Feed() {
  const visibleDates = useVisibleDates()
  return (
    <div className="space-y-12 pb-24">
      {visibleDates.map((date) => (
        <CalendarDay key={date} date={date} />
      ))}
    </div>
  )
}

export default Feed
