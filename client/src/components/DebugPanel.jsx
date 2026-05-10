import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { readApiResponse } from '../lib/apiError'
import { toYaml } from '../lib/yamlLog'
import { useFeedStatus } from '../store/articleStore'
import YamlView from './YamlView'

function readBrowserStore(store) {
  const items = {}
  for (let index = 0; index < store.length; index += 1) {
    const key = store.key(index)
    if (!key) continue
    const value = store.getItem(key)
    items[key] = {
      length: value?.length ?? 0,
      preview: value?.slice(0, 200) ?? '',
    }
  }
  const count = Object.keys(items).length
  return count === 0 ? { count: 0 } : { count, items }
}

function compactArticle(article) {
  const compact = { url: article.url }
  if (article.has_read) compact.has_read = true
  if (article.has_removed) compact.has_removed = true
  if (article.has_summary) {
    compact.summary_chars = article.summary_chars
    if (article.summary_status) compact.summary_status = article.summary_status
  }
  return compact
}

function compactDay(day) {
  const compact = {
    date: day.date,
    cached_at: day.cached_at,
    storage_updated_at: day.storage_updated_at,
    article_count: day.article_count,
  }
  if (day.has_digest) {
    compact.digest_chars = day.digest_chars
    if (day.digest_status) compact.digest_status = day.digest_status
  }
  compact.articles = (day.articles || []).map(compactArticle)
  return compact
}

function compactSupabaseSummary(summary) {
  if (!Array.isArray(summary)) return summary
  return summary.map(compactDay)
}

function ActionButton({ label, onClick, disabled = false, danger = false, accent = false }) {
  const baseClass = 'inline-flex items-center justify-center rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed'
  const colorClass = danger
    ? 'border-red-500 bg-red-500/10 text-red-400 hover:bg-red-500/20'
    : accent
      ? 'border-cyan-500 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20'
      : 'border-emerald-500 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20'
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={`${baseClass} ${colorClass}`}>
      {label}
    </button>
  )
}

function DebugPanel({ open, onClose }) {
  const feed = useFeedStatus()
  const [supabaseUrl, setSupabaseUrl] = useState(null)
  const [supabaseSummary, setSupabaseSummary] = useState(null)
  const [supabaseError, setSupabaseError] = useState(null)
  const [refreshTick, setRefreshTick] = useState(0)
  const [busy, setBusy] = useState(null)
  const [copyState, setCopyState] = useState('idle')

  useEffect(() => {
    if (!open) return
    fetch('/api/debug/supabase-url')
      .then(response => readApiResponse(response, 'GET /api/debug/supabase-url'))
      .then(data => setSupabaseUrl(data.url || '(unset)'))
      .catch(error => {
        console.error('GET /api/debug/supabase-url failed:', error)
        setSupabaseUrl(`(error: ${error.message})`)
      })
  }, [open])

  // biome-ignore lint/correctness/useExhaustiveDependencies: refreshTick is the explicit re-fetch trigger.
  useEffect(() => {
    if (!open) return
    if (!feed.startDate || !feed.endDate) return
    setSupabaseError(null)
    fetch('/api/debug/daily-cache-summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ start_date: feed.startDate, end_date: feed.endDate }),
    })
      .then(response => readApiResponse(response, 'POST /api/debug/daily-cache-summary'))
      .then(data => setSupabaseSummary(data.summary))
      .catch(error => {
        console.error('POST /api/debug/daily-cache-summary failed:', error)
        setSupabaseError(error.message)
      })
  }, [open, feed.startDate, feed.endDate, refreshTick])

  const handleClearLocal = useCallback(() => {
    setBusy('local')
    try {
      localStorage.clear()
      console.log('debug: localStorage cleared')
    } catch (error) {
      console.error('Clear localStorage failed:', error)
    } finally {
      setBusy(null)
      setRefreshTick(t => t + 1)
    }
  }, [])

  const handleClearSession = useCallback(() => {
    setBusy('session')
    try {
      sessionStorage.clear()
      console.log('debug: sessionStorage cleared')
    } catch (error) {
      console.error('Clear sessionStorage failed:', error)
    } finally {
      setBusy(null)
      setRefreshTick(t => t + 1)
    }
  }, [])

  const handleClearSupabase = useCallback(async () => {
    if (!feed.startDate || !feed.endDate) return
    const range = `${feed.startDate}..${feed.endDate}`
    if (!window.confirm(`Delete daily_cache rows for ${range}?`)) return
    setBusy('supabase')
    try {
      const response = await fetch('/api/debug/clear-daily-cache', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_date: feed.startDate, end_date: feed.endDate }),
      })
      const data = await readApiResponse(response, 'POST /api/debug/clear-daily-cache')
      console.log(`debug: cleared ${data.deleted_count ?? '?'} daily_cache rows for ${range}`)
    } catch (error) {
      console.error('Clear Supabase failed:', error)
    } finally {
      setBusy(null)
      setRefreshTick(t => t + 1)
    }
  }, [feed.startDate, feed.endDate])

  // biome-ignore lint/correctness/useExhaustiveDependencies: refreshTick is the explicit invalidator for window storage reads.
  const debugObject = useMemo(() => ({
    feed: {
      status: feed.status,
      range: feed.startDate && feed.endDate ? `${feed.startDate}..${feed.endDate}` : null,
      stats: feed.stats,
      error: feed.error,
    },
    localStorage: readBrowserStore(window.localStorage),
    sessionStorage: readBrowserStore(window.sessionStorage),
    supabase_daily_cache: supabaseError
      ? { error: supabaseError }
      : (supabaseSummary ? compactSupabaseSummary(supabaseSummary) : '(loading)'),
  }), [feed.status, feed.startDate, feed.endDate, feed.stats, feed.error, supabaseSummary, supabaseError, refreshTick])

  const globalStats = useMemo(() => {
    const range = feed.startDate && feed.endDate ? `${feed.startDate}..${feed.endDate}` : '(no range)'
    const cacheLine = supabaseError
      ? `(error: ${supabaseError})`
      : Array.isArray(supabaseSummary)
        ? `${supabaseSummary.length} day${supabaseSummary.length === 1 ? '' : 's'} · ${supabaseSummary.reduce((sum, day) => sum + (day.article_count || 0), 0)} articles`
        : '(loading)'
    return [
      { label: 'SUPABASE', value: supabaseUrl ?? '(loading)' },
      { label: 'RANGE', value: `${range}  ·  ${feed.status}` },
      { label: 'CACHE', value: cacheLine },
    ]
  }, [supabaseUrl, feed.startDate, feed.endDate, feed.status, supabaseSummary, supabaseError])

  const handleCopy = useCallback(async () => {
    const statsLines = globalStats.map(stat => `${stat.label}: ${stat.value}`).join('\n')
    const yamlText = toYaml(debugObject)
    const fullText = `${statsLines}\n\n${yamlText}`
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(fullText)
      } else {
        // Fallback for non-secure contexts
        const textarea = document.createElement('textarea')
        textarea.value = fullText
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }
      setCopyState('copied')
      setTimeout(() => setCopyState('idle'), 1500)
    } catch (error) {
      console.error('Copy to clipboard failed:', error)
      setCopyState('error')
      setTimeout(() => setCopyState('idle'), 1500)
    }
  }, [debugObject, globalStats])

  if (!open) return null

  const copyLabel = copyState === 'copied' ? 'Copied' : copyState === 'error' ? 'Copy failed' : 'Copy'

  return (
    <div className="fixed inset-0 z-[150] flex items-stretch justify-center bg-black/40 backdrop-blur-sm">
      <div className="m-4 flex max-h-[calc(100vh-2rem)] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-emerald-500/40 bg-slate-950 text-emerald-200 shadow-2xl">
        <div className="flex items-center justify-between gap-3 border-b border-emerald-500/30 px-4 py-3">
          <div className="font-mono text-xs uppercase tracking-wider text-emerald-400">Debug</div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-emerald-500/40 px-2 py-1 text-xs text-emerald-200 hover:bg-emerald-500/10"
          >
            Close
          </button>
        </div>

        <div className="flex flex-wrap gap-2 border-b border-emerald-500/20 px-4 py-3">
          <ActionButton label="Clear localStorage" onClick={handleClearLocal} disabled={busy === 'local'} danger />
          <ActionButton label="Clear sessionStorage" onClick={handleClearSession} disabled={busy === 'session'} danger />
          <ActionButton
            label={feed.startDate ? `Clear Supabase (${feed.startDate}..${feed.endDate})` : 'Clear Supabase'}
            onClick={handleClearSupabase}
            disabled={busy === 'supabase' || !feed.startDate}
            danger
          />
          <ActionButton label="Refresh" onClick={() => setRefreshTick(t => t + 1)} />
          <ActionButton label={copyLabel} onClick={handleCopy} accent />
        </div>

        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 border-b border-emerald-500/20 bg-slate-900/40 px-4 py-3 font-mono text-[11px]">
          {globalStats.map(stat => (
            <Fragment key={stat.label}>
              <dt className="text-emerald-400/80 uppercase tracking-wider">{stat.label}</dt>
              <dd className="break-all text-emerald-100">{stat.value}</dd>
            </Fragment>
          ))}
        </dl>

        <div className="flex-1 overflow-auto bg-slate-950 p-4">
          <YamlView value={debugObject} />
        </div>
      </div>
    </div>
  )
}

export default DebugPanel
