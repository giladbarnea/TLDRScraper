import { FloatingTree } from '@floating-ui/react'
import { Calendar } from 'lucide-react'
import { useEffect, useState } from 'react'
import DigestOverlay from './components/DigestOverlay'
import Feed from './components/Feed'
import ScrapeForm from './components/ScrapeForm'
import SelectionActionDock from './components/SelectionActionDock'
import ToastContainer from './components/ToastContainer'
import { InteractionProvider, useInteraction } from './contexts/InteractionContext'
import { useDigest } from './hooks/useDigest'
import { getDefaultFeedDateRange, useFeedLoader } from './hooks/useFeedLoader'
import { getCachedStorageValue, setStorageValueAsync } from './hooks/useSupabaseStorage'
import { publishArticleAction } from './lib/articleActionBus'
import { extractSelectedArticleDescriptors, getSelectedArticles, groupSelectedByDate } from './lib/selectionUtils'
import { getNewsletterScrapeKey } from './lib/storageKeys'
import { ArticleLifecycleEventType, reduceArticleLifecycle } from './reducers/articleLifecycleReducer'
import * as summaryDataReducer from './reducers/summaryDataReducer'

function getLivePayload(date, fallbackPayloads) {
  const livePayload = getCachedStorageValue(getNewsletterScrapeKey(date))
  if (livePayload) return livePayload
  return fallbackPayloads?.find((payload) => payload.date === date) || null
}

function toBrowserUrl(url) {
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  return `https://${url}`
}

async function applyBatchLifecyclePatch(selectedArticles, eventFactory) {
  const groupedArticlesByDate = groupSelectedByDate(selectedArticles)

  for (const [date, articles] of groupedArticlesByDate.entries()) {
    const selectedUrls = new Set(articles.map((article) => article.url))
    const storageKey = getNewsletterScrapeKey(date)

    await setStorageValueAsync(storageKey, (currentPayload) => {
      if (!currentPayload) return currentPayload

      return {
        ...currentPayload,
        articles: currentPayload.articles.map((article) => {
          if (!selectedUrls.has(article.url)) return article
          const event = eventFactory(article)
          return { ...article, ...reduceArticleLifecycle(article, event).patch }
        })
      }
    })
  }
}

function AppContent({ results, loadFeed, showSettings, setShowSettings }) {
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

  const livePayloads = results?.payloads
    ? results.payloads
      .map((payload) => getLivePayload(payload.date, results.payloads))
      .filter(Boolean)
    : []
  const selectedArticles = getSelectedArticles(selectedIds, livePayloads)
  const selectedDescriptors = extractSelectedArticleDescriptors(selectedArticles)
  const selectedCount = selectedIds.size
  const singleSelectedId = selectedCount === 1 ? [...selectedIds][0] : null
  const singleSelectedUrl = singleSelectedId?.startsWith('article-')
    ? singleSelectedId.slice('article-'.length)
    : null
  const singleSelectedArticle = singleSelectedUrl
    ? selectedArticles.find((article) => article.url === singleSelectedUrl) || null
    : null
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
      markedAt
    }))
    clearSelection()
  }

  async function handleMarkSelectedRemoved() {
    if (selectedArticles.length === 0) return

    await applyBatchLifecyclePatch(selectedArticles, () => ({
      type: ArticleLifecycleEventType.MARK_REMOVED
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

          <div className={`
              overflow-hidden transition-all duration-500 ease-in-out
              ${showSettings ? 'max-h-[400px] opacity-100 mt-4' : 'max-h-0 opacity-0'}
          `}>
            <div className="bg-white rounded-2xl p-5 shadow-elevated border border-slate-200/50">
              <ScrapeForm
                loadFeed={loadFeed}
                onSuccess={() => setShowSettings(false)}
              />
            </div>
          </div>
        </header>

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

      {digest.expanded && (
        <DigestOverlay
          html={digest.html}
          markdown={digest.markdown}
          articleUrls={digest.articleUrls}
          articleCount={digest.articleCount}
          errorMessage={digest.errorMessage}
          onClose={() => digest.collapse(false)}
          onMarkRemoved={() => digest.collapse(true)}
        />
      )}

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
  const { results, setResults, loadFeed } = useFeedLoader()
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
    const { startDate, endDate } = getDefaultFeedDateRange()

    loadFeed({
      startDate,
      endDate,
      signal: controller.signal,
      useSessionCache: true
    }).catch((error) => {
      if (error.name === 'AbortError') return
      console.error('Failed to load feed:', error)
      setResults((previousResults) => previousResults ?? { payloads: [], stats: null })
    })

    return () => controller.abort()
  }, [loadFeed, setResults])

  return (
    <InteractionProvider>
      <ToastContainer />
      <FloatingTree>
        <AppContent
          results={results}
          loadFeed={loadFeed}
          showSettings={showSettings}
          setShowSettings={setShowSettings}
        />
      </FloatingTree>
    </InteractionProvider>
  )
}

export default App
