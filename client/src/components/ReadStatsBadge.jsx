function ReadStatsBadge({ completedCount, totalCount }) {
  if (!totalCount) return null

  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 text-slate-400 text-xs tabular-nums">
      {completedCount}/{totalCount}
    </span>
  )
}

export default ReadStatsBadge
