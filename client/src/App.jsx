import { FloatingTree } from '@floating-ui/react'
import { Bug, Calendar } from 'lucide-react'
import { useEffect, useState } from 'react'
import DebugPanel from './components/DebugPanel'
import DigestOverlay from './components/DigestOverlay'
import Feed from './components/Feed'
import ScrapeForm from './components/ScrapeForm'
import SelectionActionDock from './components/SelectionActionDock'
import ToastContainer from './components/ToastContainer'
import { useDigest } from './hooks/useDigest'
import { getDefaultFeedDateRange, useFeedLoader } from './hooks/useFeedLoader'
import { queueBatchArticlePatches } from './lib/dailyPayloadMutations'
import { ArticleLifecycleEventType, reduceArticleLifecycle } from './reducers/articleLifecycleReducer'
import * as summaryDataReducer from './reducers/summaryDataReducer'
import {
  getSnapshotArticle,
  interactionActions,
  summaryActions,
  useFeedStatus,
  useIsSelectMode,
  useSelectedArticles,
  useVisibleDates,
} from './store/articleStore'

function toBrowserUrl(url) {
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  return `https://${url}`
}

async function applyBatchLifecyclePatch(selectedArticles, eventFactory) {
  const patches = selectedArticles.map(({ key }) => ({
    key,
    buildPatch: (currentArticle) => reduceArticleLifecycle(currentArticle, eventFactory(currentArticle)).patch,
  }))
  await queueBatchArticlePatches(patches)
}

function AppContent({ loadFeed, showSettings, setShowSettings, showDebug, setShowDebug }) {
  const feedStatus = useFeedStatus()
  const visibleDates = useVisibleDates()
  const digest = useDigest()
  const isSelectMode = useIsSelectMode()
  const selectedArticles = useSelectedArticles()
  const selectedCount = selectedArticles.length

  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric'
  })

  const singleDescriptor = selectedCount === 1 ? selectedArticles[0] : null
  const singleSelectedArticle = singleDescriptor ? getSnapshotArticle(singleDescriptor.key) : null
  const singleSummaryStatus = summaryDataReducer.getSummaryDataStatus(singleSelectedArticle?.summary)
  const canOpenSingleSummary = singleSummaryStatus === summaryDataReducer.SummaryDataStatus.AVAILABLE
  const isSingleSummaryLoading = singleSummaryStatus === summaryDataReducer.SummaryDataStatus.LOADING
  const summarizeEachActionableCount = selectedArticles.filter(({ key }) => {
    const article = getSnapshotArticle(key)
    const status = summaryDataReducer.getSummaryDataStatus(article?.summary)
    return status === summaryDataReducer.SummaryDataStatus.UNKNOWN || status === summaryDataReducer.SummaryDataStatus.ERROR
  }).length
  const isSummarizeEachDisabled = selectedCount < 2 || summarizeEachActionableCount === 0

  function handleTriggerDigest() {
    digest.trigger(selectedArticles)
  }

  async function handleMarkSelectedRead() {
    if (selectedCount === 0) return
    const markedAt = new Date().toISOString()
    await applyBatchLifecyclePatch(selectedArticles, () => ({
      type: ArticleLifecycleEventType.MARK_READ,
      markedAt,
    }))
    interactionActions.clearSelection()
  }

  async function handleMarkSelectedRemoved() {
    if (selectedCount === 0) return
    await applyBatchLifecyclePatch(selectedArticles, () => ({
      type: ArticleLifecycleEventType.MARK_REMOVED,
    }))
    interactionActions.clearSelection()
  }

  function handleSummarizeSingle() {
    if (!singleDescriptor) return
    if (canOpenSingleSummary) {
      summaryActions.expand(singleDescriptor.key)
      return
    }
    summaryActions.fetch(singleDescriptor.key)
  }

  function handleBrowseSingle() {
    if (!singleSelectedArticle) return
    window.open(toBrowserUrl(singleSelectedArticle.url), '_blank', 'noopener,noreferrer')
  }

  function handleSummarizeEach() {
    if (selectedCount < 2) return
    for (const { key } of selectedArticles) {
      const article = getSnapshotArticle(key)
      if (!article) continue
      const status = summaryDataReducer.getSummaryDataStatus(article.summary)
      if (status === summaryDataReducer.SummaryDataStatus.UNKNOWN || status === summaryDataReducer.SummaryDataStatus.ERROR) {
        summaryActions.fetch(key)
      }
    }
  }

  const isLoadingInitial = feedStatus.status === 'idle' || feedStatus.status === 'fetching'
  const hasContent = visibleDates.length > 0
  const isError = feedStatus.status === 'error' && !hasContent

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
                onClick={() => setShowDebug(!showDebug)}
                className={`group flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300 ${showDebug ? 'bg-emerald-50 text-emerald-600' : 'hover:bg-white hover:shadow-md text-slate-400'}`}
                title="Debug Panel"
              >
                <Bug size={18} className="transition-colors" />
              </button>
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
          {isLoadingInitial && !hasContent ? (
            <div className="flex flex-col items-center justify-center py-32 opacity-50 animate-pulse">
              <div className="w-12 h-12 bg-slate-200 rounded-full mb-4"></div>
              <div className="h-4 w-32 bg-slate-200 rounded mb-2"></div>
              <div className="h-3 w-24 bg-slate-100 rounded"></div>
            </div>
          ) : hasContent ? (
            <Feed />
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-32 text-slate-400">
              <p>Failed to load feed.</p>
              <button onClick={() => setShowSettings(true)} className="mt-4 text-brand-600 font-medium hover:underline">
                Open settings to retry
              </button>
            </div>
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
        onClearSelection={interactionActions.clearSelection}
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
  const { loadFeed } = useFeedLoader()
  const [showSettings, setShowSettings] = useState(false)
  const [showDebug, setShowDebug] = useState(false)

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
    }).catch((error) => {
      if (error.name === 'AbortError') return
      console.error('Failed to load feed:', error)
    })

    return () => controller.abort()
  }, [loadFeed])

  return (
    <>
      <ToastContainer />
      <FloatingTree>
        <AppContent
          loadFeed={loadFeed}
          showSettings={showSettings}
          setShowSettings={setShowSettings}
          showDebug={showDebug}
          setShowDebug={setShowDebug}
        />
      </FloatingTree>
      <DebugPanel open={showDebug} onClose={() => setShowDebug(false)} />
    </>
  )
}

export default App
