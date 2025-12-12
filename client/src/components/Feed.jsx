import CalendarDay from './CalendarDay'
import { ZenModeProvider } from './ZenModeContext'

function Feed({ payloads }) {
  return (
    <ZenModeProvider>
      <div className="space-y-16 pb-32">
        {payloads.map((payload) => (
          <CalendarDay key={payload.date} payload={payload} />
        ))}
      </div>
    </ZenModeProvider>
  )
}

export default Feed
