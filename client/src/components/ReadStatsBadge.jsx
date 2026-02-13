function ReadStatsBadge({ articles }) {
  if (!articles || articles.length === 0) return null

  const total = articles.length
  const completedCount = articles.filter(a => a.read?.isRead || a.removed).length

  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 text-slate-400 text-xs tabular-nums">
      {completedCount}/{total}
    </span>
  )
}

export default ReadStatsBadge
