import CalendarDay from './CalendarDay'

function Feed({ payloads }) {
  return (
    <div className="space-y-16 pb-32">
      {payloads.map((payload) => (
        <CalendarDay key={payload.date} payload={payload} />
      ))}
    </div>
  )
}

export default Feed
