import CalendarDay from './CalendarDay'

function Feed({ payloads }) {
  return (
    <div className="space-y-12 pb-24">
      {payloads.map((payload) => (
        <CalendarDay key={payload.date} payload={payload} />
      ))}
    </div>
  )
}

export default Feed
