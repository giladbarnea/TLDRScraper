/**
 * Logs state transitions for ArticleCard domains.
 * Domain A: Lifecycle (unread, read, removed)
 * Domain B: Summary data (unknown, loading, available, error)
 * Domain C: Summary view (collapsed, expanded)
 * Domain D: Gesture (idle, dragging)
 */

function truncateUrl(url) {
  if (!url) return '?'
  try {
    const parsed = new URL(url)
    const path = parsed.pathname.split('/').filter(Boolean).pop() || parsed.hostname
    return path.length > 30 ? path.slice(0, 30) + '...' : path
  } catch {
    return url.slice(0, 30)
  }
}

export function logTransition(domain, url, from, to, extra = '') {
  const label = truncateUrl(url)
  const extraStr = extra ? ` (${extra})` : ''
  console.log(`[${domain}] ${label}: ${from} → ${to}${extraStr}`)
}

export function logTransitionSuccess(domain, url, to, extra = '') {
  const label = truncateUrl(url)
  const extraStr = extra ? ` (${extra})` : ''
  console.log(`[${domain}] ${label}: → ${to} ✓${extraStr}`)
}
