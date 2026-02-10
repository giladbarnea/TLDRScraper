import { Calendar } from 'lucide-react'
import { useEffect, useState } from 'react'
import Feed from './components/Feed'
import ScrapeForm from './components/ScrapeForm'
import SelectionCounterPill from './components/SelectionCounterPill'
import { InteractionProvider } from './contexts/InteractionContext'
import { mergeIntoCache } from './hooks/useSupabaseStorage'
import { scrapeNewsletters } from './lib/scraper'
import { logTransition } from './lib/stateTransitionLogger'
import { getDailyPayloadsRange } from './lib/storageApi'
import { getNewsletterScrapeKey } from './lib/storageKeys'

function mergePreservingLocalState(freshPayload, localPayload) {
  if (!localPayload) return freshPayload
  const localByUrl = new Map(localPayload.articles.map(a => [a.url, a]))
  return {
    ...freshPayload,
    articles: freshPayload.articles.map(article => {
      const local = localByUrl.get(article.url)
      if (!local) return article
      return { ...article, tldr: local.tldr, read: local.read, removed: local.removed }
    })
  }
}

function App() {
  const [results, setResults] = useState(null)
  const [showSettings, setShowSettings] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller

    const today = new Date()
    const twoDaysAgo = new Date(today)
    twoDaysAgo.setDate(today.getDate() - 2)

    const endDate = today.toISOString().split('T')[0]
    const startDate = twoDaysAgo.toISOString().split('T')[0]

    const cacheKey = `scrapeResults:${startDate}:${endDate}`
    const TTL_MS = 10 * 60 * 1000

    const range = `${startDate}..${endDate}`

    const sessionCached = sessionStorage.getItem(cacheKey)
    if (sessionCached) {
      const { timestamp, data } = JSON.parse(sessionCached)
      if (Date.now() - timestamp < TTL_MS) {
        logTransition('feed', range, 'idle', 'ready', 'sessionStorage')
        setResults(data)
        return
      }
    }

    async function loadFeed() {
      let phase1Rendered = false

      logTransition('feed', range, 'idle', 'fetching')
      const cachePromise = getDailyPayloadsRange(startDate, endDate, signal).catch(() => [])
      const scrapePromise = scrapeNewsletters(startDate, endDate, signal)

      // Phase 1: render cached data immediately
      const cachedPayloads = await cachePromise
      if (signal.aborted) return
      if (cachedPayloads.length > 0) {
        phase1Rendered = true
        const articleCount = cachedPayloads.reduce((sum, p) => sum + p.articles.length, 0)
        logTransition('feed', range, 'fetching', 'cached', `${cachedPayloads.length} days, ${articleCount} articles`)
        setResults({ payloads: cachedPayloads, stats: null })
      }

      // Phase 2: merge background scrape results
      const result = await scrapePromise
      if (signal.aborted) return

      if (phase1Rendered) {
        const cachedDates = new Set(cachedPayloads.map(p => p.date))
        const cachedUrlsByDate = new Map(
          cachedPayloads.map(p => [p.date, new Set(p.articles.map(a => a.url))])
        )
        let newArticleCount = 0
        for (const freshPayload of result.payloads) {
          if (cachedDates.has(freshPayload.date)) {
            const cachedUrls = cachedUrlsByDate.get(freshPayload.date)
            newArticleCount += freshPayload.articles.filter(a => !cachedUrls.has(a.url)).length
            mergeIntoCache(
              getNewsletterScrapeKey(freshPayload.date),
              local => mergePreservingLocalState(freshPayload, local)
            )
          }
        }
        const newDayPayloads = result.payloads.filter(p => !cachedDates.has(p.date))
        if (newDayPayloads.length > 0) {
          setResults(prev => ({
            ...result,
            payloads: [...(prev?.payloads || []), ...newDayPayloads]
          }))
        }
        logTransition('feed', range, 'cached', 'merged', `${newArticleCount} new articles, ${newDayPayloads.length} new days`)
      } else {
        const articleCount = result.payloads.reduce((sum, p) => sum + p.articles.length, 0)
        logTransition('feed', range, 'fetching', 'ready', `${result.payloads.length} days, ${articleCount} articles`)
        setResults(result)
      }

      try {
        sessionStorage.setItem(cacheKey, JSON.stringify({ timestamp: Date.now(), data: result }))
      } catch {}
    }

    loadFeed().catch(err => {
      if (err.name === 'AbortError') return
      console.error('Failed to load feed:', err)
      setResults(prev => prev ?? { payloads: [], stats: null })
    })

    return () => controller.abort()
  }, [])

  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric'
  })

  return (
    <InteractionProvider>
    <div className="min-h-screen flex justify-center font-sans bg-slate-50 text-slate-900 selection:bg-brand-100 selection:text-brand-900">
      <div className="w-full max-w-3xl relative">

        {/* Header */}
        <header className="relative z-40 px-6 pt-6 pb-2 bg-transparent">
          <div className="flex justify-between items-center">
            <div>
              <a href="/api/source" className="inline-block">
                <h1 className="font-display text-[28px] font-extrabold tracking-tight text-slate-900 hover:text-brand-600 transition-colors cursor-pointer">
                  TLDR<span className="text-brand-500">.</span>
                </h1>
              </a>
              <p className="text-sm font-medium text-slate-500 mt-0.5">
                {currentDate}
              </p>
            </div>

            <div className="flex items-center gap-3">
              <SelectionCounterPill />
              <button
                onClick={() => setShowSettings(!showSettings)}
                className={`group flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300 ${showSettings ? 'bg-brand-50 text-brand-600' : 'hover:bg-white hover:shadow-md text-slate-400'}`}
                title="Date Range & Settings"
              >
                <Calendar size={18} className="transition-colors" />
              </button>
            </div>
          </div>

          {/* Settings / Scrape Form Area */}
          <div className={`
              overflow-hidden transition-all duration-500 ease-in-out
              ${showSettings ? 'max-h-[400px] opacity-100 mt-4' : 'max-h-0 opacity-0'}
          `}>
             <div className="bg-white rounded-2xl p-5 shadow-elevated border border-slate-200/50">
                <ScrapeForm onResults={(res) => { setResults(res); setShowSettings(false); }} />
             </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="px-6">
          {!results ? (
             <div className="flex flex-col items-center justify-center py-32 opacity-50 animate-pulse">
                <div className="w-12 h-12 bg-slate-200 rounded-full mb-4"></div>
                <div className="h-4 w-32 bg-slate-200 rounded mb-2"></div>
                <div className="h-3 w-24 bg-slate-100 rounded"></div>
             </div>
          ) : (results.payloads && results.payloads.length > 0) ? (
            <Feed payloads={results.payloads} />
          ) : (
            <div className="flex flex-col items-center justify-center py-32 text-slate-400">
               <p>No newsletters found for this period.</p>
               <button onClick={() => setShowSettings(true)} className="mt-4 text-brand-600 font-medium hover:underline">
                 Open settings to scrape
               </button>
            </div>
          )}
        </main>

      </div>
    </div>
    </InteractionProvider>
  )
}

export default App
