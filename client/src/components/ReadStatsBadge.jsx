import { useCompletedArticlesCount } from '../store/articleStore'

function ReadStatsBadge({ date, urls }) {
  const safeUrls = urls ?? []
  const total = safeUrls.length
  const completedCount = useCompletedArticlesCount(date, safeUrls)

  if (total === 0) return null

  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 text-slate-400 text-xs tabular-nums">
      {completedCount}/{total}
    </span>
  )
}

export default ReadStatsBadge
