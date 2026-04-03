import { Calendar } from 'lucide-react'
import { useEffect, useState } from 'react'
import DigestOverlay from './components/DigestOverlay'
import Feed from './components/Feed'
import ScrapeForm from './components/ScrapeForm'
import SelectionActionDock from './components/SelectionActionDock'
import ToastContainer from './components/ToastContainer'
import { InteractionProvider, useInteraction } from './contexts/InteractionContext'
import { useDigest } from './hooks/useDigest'
import { getCachedStorageValue, mergeIntoCache, setStorageValueAsync } from './hooks/useSupabaseStorage'
import { publishArticleAction } from './lib/articleActionBus'
import { scrapeNewsletters } from './lib/scraper'
import { logTransition } from './lib/stateTransitionLogger'
import { getDailyPayloadsRange } from './lib/storageApi'
import { getNewsletterScrapeKey } from './lib/storageKeys'
import { ArticleLifecycleEventType, reduceArticleLifecycle } from './reducers/articleLifecycleReducer'
import * as summaryDataReducer from './reducers/summaryDataReducer'

const SERVER_ORIGIN_FIELDS = ['url', 'title', 'articleMeta', 'issueDate', 'category', 'sourceId', 'section', 'sectionEmoji', 'sectionOrder', 'newsletterType']

function mergePreservingLocalState(freshPayload, localPayload) {
  if (!localPayload) return freshPayload
  const localByUrl = new Map(localPayload.articles.map(a => [a.url, a]))
  return {
    ...freshPayload,
    articles: freshPayload.articles.map(article => {
      const local = localByUrl.get(article.url)
      if (!local) return { ...article, issueDate: freshPayload.date }
      const freshFields = {}
      for (const k of SERVER_ORIGIN_FIELDS) freshFields[k] = article[k]
      freshFields.issueDate = freshPayload.date
      return { ...local, ...freshFields }
    }),
    digest: localPayload.digest
  }
}

function getLivePayload(date, fallbackPayloads) {
  const live = getCachedStorageValue(getNewsletterScrapeKey(date))
  if (live) return live
  return fallbackPayloads?.find((payload) => payload.date === date) || null
}

function getSelectedArticles(selectedIds, payloads) {
  if (!payloads) return []
  const selectedArticles = []

  for (const payload of payloads) {
    const livePayload = getLivePayload(payload.date, payloads)
    if (!livePayload?.articles) continue

    for (const article of livePayload.articles) {
      if (selectedIds.has(`article-${article.url}`)) {
        selectedArticles.push(article)
      }
    }
  }

  return selectedArticles
}

function extractSelectedArticleDescriptors(selectedArticles) {
  return selectedArticles.map(({ url, title, category, sourceId }) => ({ url, title, category, sourceId }))
}

function groupSelectedByDate(selectedArticles) {
  const grouped = new Map()
  for (const article of selectedArticles) {
    if (!grouped.has(article.issueDate)) grouped.set(article.issueDate, [])
    grouped.get(article.issueDate).push(article)
  }
  return grouped
}

function toBrowserUrl(url) {
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  return `https://${url}`
}

async function applyBatchLifecyclePatch(selectedArticles, eventFactory) {
  const groupedByDate = groupSelectedByDate(selectedArticles)

  for (const [date, articles] of groupedByDate.entries()) {
    const urlSet = new Set(articles.map((article) => article.url))
    const storageKey = getNewsletterScrapeKey(date)
    await setStorageValueAsync(storageKey, (current) => {
      if (!current) return current
      return {
        ...current,
        articles: current.articles.map((article) => {
          if (!urlSet.has(article.url)) return article
          const event = eventFactory(article)
          return { ...article, ...reduceArticleLifecycle(article, event).patch }
        })
      }
    })
  }
}

function AppContent({ results, setResults, showSettings, setShowSettings }) {
  const { selectedIds, isSelectMode, clearSelection } = useInteraction()
  const digest = useDigest(results)
  const [, setStorageVersion] = useState(0)

  useEffect(() => {
    const handleStorageChange = () => setStorageVersion((version) => version + 1)
    window.addEventListener('supabase-storage-change', handleStorageChange)
    return () => window.removeEventListener('supabase-storage-change', handleStorageChange)
  }, [])

  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric'
  })
  const selectedArticles = getSelectedArticles(selectedIds, results?.payloads)
  const selectedDescriptors = extractSelectedArticleDescriptors(selectedArticles)
  const selectedCount = selectedArticles.length
  const singleSelectedArticle = selectedCount === 1 ? selectedArticles[0] : null
  const singleSummaryStatus = summaryDataReducer.getSummaryDataStatus(singleSelectedArticle?.summary)
  const canOpenSingleSummary = singleSummaryStatus === summaryDataReducer.SummaryDataStatus.AVAILABLE
  const isSingleSummaryLoading = singleSummaryStatus === summaryDataReducer.SummaryDataStatus.LOADING
  const summarizeEachActionableCount = selectedArticles.filter((article) => {
    const status = summaryDataReducer.getSummaryDataStatus(article.summary)
    return status === summaryDataReducer.SummaryDataStatus.UNKNOWN || status === summaryDataReducer.SummaryDataStatus.ERROR
  }).length
  const isSummarizeEachDisabled = selectedCount < 2 || summarizeEachActionableCount === 0

  function handleTriggerDigest() {
    digest.trigger(selectedDescriptors)
  }

  async function handleMarkSelectedRead() {
    if (selectedArticles.length === 0) return
    const markedAt = new Date().toISOString()
    await applyBatchLifecyclePatch(selectedArticles, () => ({
      type: ArticleLifecycleEventType.MARK_READ,
      markedAt,
    }))
    clearSelection()
  }

  async function handleMarkSelectedRemoved() {
    if (selectedArticles.length === 0) return
    await applyBatchLifecyclePatch(selectedArticles, () => ({
      type: ArticleLifecycleEventType.MARK_REMOVED,
    }))
    clearSelection()
  }

  function handleSummarizeSingle() {
    if (!singleSelectedArticle) return
    if (canOpenSingleSummary) {
      publishArticleAction([singleSelectedArticle.url], 'open-summary')
      return
    }
    publishArticleAction([singleSelectedArticle.url], 'fetch-summary')
  }

  function handleBrowseSingle() {
    if (!singleSelectedArticle) return
    window.open(toBrowserUrl(singleSelectedArticle.url), '_blank', 'noopener,noreferrer')
  }

  function handleSummarizeEach() {
    if (selectedCount < 2) return
    const actionableUrls = selectedArticles
      .filter((article) => {
        const status = summaryDataReducer.getSummaryDataStatus(article.summary)
        return status === summaryDataReducer.SummaryDataStatus.UNKNOWN || status === summaryDataReducer.SummaryDataStatus.ERROR
      })
      .map((article) => article.url)
    if (actionableUrls.length === 0) return
    publishArticleAction(actionableUrls, 'fetch-summary')
  }

  return (
    <div className="min-h-screen flex justify-center font-sans bg-slate-50 text-slate-900 selection:bg-brand-100 selection:text-brand-900">
      <div className="w-full max-w-3xl relative">

        {/* Header */}
        <header className="relative z-40 px-6 pt-6 pb-4 bg-transparent">
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

      <DigestOverlay
        html={digest.html}
        expanded={digest.expanded}
        articleCount={digest.articleCount}
        errorMessage={digest.errorMessage}
        onClose={() => digest.collapse(false)}
        onMarkRemoved={() => digest.collapse(true)}
      />

      <SelectionActionDock
        isSelectMode={isSelectMode}
        selectedCount={selectedCount}
        isDigestLoading={digest.loading}
        canOpenSingleSummary={canOpenSingleSummary}
        isSingleSummaryLoading={isSingleSummaryLoading}
        isSummarizeEachDisabled={isSummarizeEachDisabled}
        onClearSelection={clearSelection}
        onMarkRead={handleMarkSelectedRead}
        onMarkRemoved={handleMarkSelectedRemoved}
        onTriggerDigest={handleTriggerDigest}
        onSummarizeSingle={handleSummarizeSingle}
        onBrowseSingle={handleBrowseSingle}
        onSummarizeEach={handleSummarizeEach}
      />
    </div>
  )
}

function App() {
  const [results, setResults] = useState(null)
  const [showSettings, setShowSettings] = useState(false)

  useEffect(() => {
    let firstFrameId = 0
    let secondFrameId = 0
    let idleCallbackId = 0
    let timeoutId = 0

    const warmZenOverlayFont = () => {
      document.fonts.load('1em Lora')
    }

    const scheduleWarmup = () => {
      if ('requestIdleCallback' in window) {
        idleCallbackId = window.requestIdleCallback(warmZenOverlayFont, { timeout: 1500 })
        return
      }
      timeoutId = window.setTimeout(warmZenOverlayFont, 0)
    }

    firstFrameId = window.requestAnimationFrame(() => {
      secondFrameId = window.requestAnimationFrame(scheduleWarmup)
    })

    return () => {
      window.cancelAnimationFrame(firstFrameId)
      window.cancelAnimationFrame(secondFrameId)
      if ('cancelIdleCallback' in window && idleCallbackId) {
        window.cancelIdleCallback(idleCallbackId)
      }
      window.clearTimeout(timeoutId)
    }
  }, [])

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
      
      // Phase 1: render cached data immediately
      const cachedPayloads = await getDailyPayloadsRange(startDate, endDate, signal).catch(() => [])
      if (signal.aborted) return
      
      if (cachedPayloads.length > 0) {
        phase1Rendered = true
        const articleCount = cachedPayloads.reduce((sum, p) => sum + p.articles.length, 0)
        logTransition('feed', range, 'fetching', 'cached', `${cachedPayloads.length} days, ${articleCount} articles`)
        setResults({ payloads: cachedPayloads, stats: null })
      }

      // Phase 2: merge background scrape results
      const result = await scrapeNewsletters(startDate, endDate, signal)
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

  return (
    <InteractionProvider>
      <ToastContainer />
      <AppContent
        results={results}
        setResults={setResults}
        showSettings={showSettings}
        setShowSettings={setShowSettings}
      />
    </InteractionProvider>
  )
}

export default App
