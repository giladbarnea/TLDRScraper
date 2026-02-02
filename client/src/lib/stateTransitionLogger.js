/**
 * Logs state transitions for ArticleCard domains.
 * Domain A: Lifecycle (unread, read, removed)
 * Domain B: Summary data (unknown, loading, available, error)
 * Domain C: Summary view (collapsed, expanded)
 * Domain D: Gesture (idle, dragging)
 */

const DOMAIN_COLORS = {
  lifecycle: '#8be9fd',
  'summary-data': '#ffb86c',
  'summary-view': '#ff79c6',
  gesture: '#bd93f9'
}

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
  const color = DOMAIN_COLORS[domain] || '#fff'
  const extraStr = extra ? ` (${extra})` : ''
  console.log(`%c[${domain}]%c ${label}: ${from} → ${to}${extraStr}`, `color:${color};font-weight:bold`, 'color:inherit')
}

export function logTransitionSuccess(domain, url, to, extra = '') {
  const label = truncateUrl(url)
  const color = DOMAIN_COLORS[domain] || '#fff'
  const extraStr = extra ? ` (${extra})` : ''
  console.log(`%c[${domain}]%c ${label}: → ${to} %c\u2713${extraStr}`, `color:${color};font-weight:bold`, 'color:inherit', 'color:#50fa7b')
}
