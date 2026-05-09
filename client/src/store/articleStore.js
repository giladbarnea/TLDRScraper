import { useSyncExternalStore } from 'react'
import { createRequestToken } from '../lib/requestUtils'
import { logTransition, logTransitionSuccess } from '../lib/stateTransitionLogger'
import { emitToast } from '../lib/toastBus'
import { acquireZenLock, releaseZenLock } from '../lib/zenLock'
import { interactionReduce } from '../reducers/interactionReducer'
import * as summaryDataReducer from '../reducers/summaryDataReducer'

// ─── Identity ────────────────────────────────────────────────────────────────

function articleKey(date, url) {
  return `${date}::${url}`
}

export function parseArticleKey(key) {
  const sep = key.indexOf('::')
  return { date: key.slice(0, sep), url: key.slice(sep + 2) }
}

// ─── Storage ─────────────────────────────────────────────────────────────────

const articlesByKey = new Map()  // ArticleKey → article slice
const daysByDate = new Map()     // date → day slice (with ordered articleKeys)

let feed = {
  startDate: null,
  endDate: null,
  status: 'idle',  // 'idle' | 'fetching' | 'cached' | 'ready' | 'error'
  stats: null,
  error: null,
  visibleDates: [],
}

const SERVER_ORIGIN_ARTICLE_FIELDS = [
  'url',
  'title',
  'articleMeta',
  'category',
  'sourceId',
  'section',
  'sectionEmoji',
  'sectionOrder',
  'newsletterType',
]

// ─── Listeners ───────────────────────────────────────────────────────────────

const articleListeners = new Map()    // articleKey → Set<() => void>
const dayListeners = new Map()        // date → Set<() => void>
const feedListeners = new Set()
const containerListeners = new Map()  // containerId → Set<() => void>
const anySelectedListeners = new Set()

function notifyArticle(key) {
  articleListeners.get(key)?.forEach(listener => { listener() })
}

function notifyDay(date) {
  dayViewCache.delete(date)
  newsletterViewCache.delete(date)
  dayListeners.get(date)?.forEach(listener => { listener() })
}

function notifyFeed() {
  feedListeners.forEach(listener => { listener() })
}

function notifyContainer(containerId) {
  containerListeners.get(containerId)?.forEach(listener => { listener() })
}

function notifyAnySelected() {
  anySelectedListeners.forEach(listener => { listener() })
}

// ─── Auxiliary (interaction) ─────────────────────────────────────────────────

const EXPANDED_STORAGE_KEY = 'expandedContainers:v1'

function loadExpandedFromStorage() {
  try {
    const raw = localStorage.getItem(EXPANDED_STORAGE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    return new Set(Array.isArray(arr) ? arr : [])
  } catch {
    return new Set()
  }
}

let auxiliary = {
  expandedContainerIds: loadExpandedFromStorage(),
  suppressNextShortPress: { id: null, untilMs: 0 },
  selectedCount: 0,
}

function saveExpandedToStorage(expandedSet) {
  try {
    localStorage.setItem(EXPANDED_STORAGE_KEY, JSON.stringify([...expandedSet]))
  } catch {}
}

// ─── Async network state (per-article) ───────────────────────────────────────

const abortControllers = new Map()
const requestTokens = new Map()
const previousSummaryData = new Map()

// ─── Derived view caches ─────────────────────────────────────────────────────

const dayViewCache = new Map()        // date → DayView snapshot
const newsletterViewCache = new Map() // date → Map<sourceId, NewsletterView>

// ─── Ingestion ───────────────────────────────────────────────────────────────

function buildArticleSlice(existing, incoming, date, originalOrder) {
  const slice = {
    issueDate: date,
    originalOrder,
    expandedView: existing?.expandedView ?? false,
    selected: existing?.selected ?? false,
  }
  for (const field of SERVER_ORIGIN_ARTICLE_FIELDS) {
    slice[field] = incoming[field]
  }
  if (existing) {
    slice.read = existing.read ?? null
    slice.removed = Boolean(existing.removed)
    slice.summary = existing.summary ?? null
  } else {
    slice.read = incoming.read ?? null
    slice.removed = Boolean(incoming.removed)
    slice.summary = incoming.summary ?? null
  }
  return slice
}

function ingestSingleDay(payload) {
  const date = payload.date
  const nextKeys = []
  const changedKeys = []
  let selectedAggregateChanged = false
  let staleSelectedCount = 0

  payload.articles.forEach((article, index) => {
    const key = articleKey(date, article.url)
    nextKeys.push(key)
    const existing = articlesByKey.get(key)
    const next = buildArticleSlice(existing, article, date, index)
    articlesByKey.set(key, next)
    changedKeys.push(key)
    if (next.selected || existing?.selected) selectedAggregateChanged = true
  })

  const nextKeySet = new Set(nextKeys)
  const previousDay = daysByDate.get(date)
  const previousKeys = previousDay?.articleKeys ?? []
  const staleKeys = []
  for (const key of previousKeys) {
    if (nextKeySet.has(key)) continue
    const stale = articlesByKey.get(key)
    if (stale?.selected) {
      staleSelectedCount += 1
      selectedAggregateChanged = true
    }
    abortControllers.get(key)?.abort()
    abortControllers.delete(key)
    requestTokens.delete(key)
    previousSummaryData.delete(key)
    articlesByKey.delete(key)
    staleKeys.push(key)
  }

  daysByDate.set(date, {
    date,
    issues: payload.issues ?? [],
    digest: payload.digest ?? null,
    storage_updated_at: payload.storage_updated_at ?? null,
    articleKeys: nextKeys,
  })

  if (staleSelectedCount > 0) {
    auxiliary = { ...auxiliary, selectedCount: auxiliary.selectedCount - staleSelectedCount }
  }

  return {
    changedKeys,
    staleKeys,
    selectedAggregateChanged,
  }
}

function recomputeVisibleDates() {
  const dates = [...daysByDate.keys()].sort()
  const start = feed.startDate
  const end = feed.endDate
  const filtered = (start && end)
    ? dates.filter(date => date >= start && date <= end)
    : dates
  feed = { ...feed, visibleDates: filtered }
}

export function ingestFeedPayloads(payloads) {
  const allChangedKeys = []
  const allStaleKeys = []
  const affectedDates = []
  let selectedAggregateChanged = false

  for (const payload of payloads) {
    const result = ingestSingleDay(payload)
    allChangedKeys.push(...result.changedKeys)
    allStaleKeys.push(...result.staleKeys)
    affectedDates.push(payload.date)
    if (result.selectedAggregateChanged) selectedAggregateChanged = true
  }

  recomputeVisibleDates()
  if (selectedAggregateChanged) recomputeSelectedArticles()

  allChangedKeys.forEach(notifyArticle)
  allStaleKeys.forEach(notifyArticle)
  affectedDates.forEach(notifyDay)
  notifyFeed()
  if (selectedAggregateChanged) notifyAnySelected()
}

export function ingestDayPayload(payload) {
  const result = ingestSingleDay(payload)
  recomputeVisibleDates()
  if (result.selectedAggregateChanged) recomputeSelectedArticles()

  result.changedKeys.forEach(notifyArticle)
  result.staleKeys.forEach(notifyArticle)
  notifyDay(payload.date)
  notifyFeed()
  if (result.selectedAggregateChanged) notifyAnySelected()
}

// ─── Feed state ──────────────────────────────────────────────────────────────

export function setFeedStatus(patch) {
  feed = { ...feed, ...patch }
  notifyFeed()
}

export function setFeedRange(startDate, endDate) {
  feed = { ...feed, startDate, endDate }
  recomputeVisibleDates()
  notifyFeed()
}

// ─── Compose payload for server (mutation queue helper) ─────────────────────

export function composeDayPayloadForServer(date) {
  const day = daysByDate.get(date)
  if (!day) return null
  const articles = day.articleKeys
    .map(key => articlesByKey.get(key))
    .filter(Boolean)
    .map(sliceToArticle)
  return {
    date,
    issues: day.issues,
    digest: day.digest,
    storage_updated_at: day.storage_updated_at,
    articles,
  }
}

function sliceToArticle(slice) {
  const { expandedView, selected, originalOrder, ...articleFields } = slice
  return { originalOrder, ...articleFields }
}

// ─── Write actions ───────────────────────────────────────────────────────────

export function applyArticlePatch(key, patch) {
  const current = articlesByKey.get(key)
  if (!current) return
  const next = { ...current, ...patch }
  articlesByKey.set(key, next)

  const date = parseArticleKey(key).date
  const lifecycleChanged = (
    Boolean(current.removed) !== Boolean(next.removed)
    || Boolean(current.read?.isRead) !== Boolean(next.read?.isRead)
  )
  const selectedAggregateChanged = current.selected || next.selected

  if ('selected' in patch) {
    const delta = (patch.selected ? 1 : 0) - (current.selected ? 1 : 0)
    if (delta !== 0) auxiliary = { ...auxiliary, selectedCount: auxiliary.selectedCount + delta }
  }

  if (selectedAggregateChanged) recomputeSelectedArticles()

  notifyArticle(key)
  if (lifecycleChanged || 'summary' in patch) notifyDay(date)
  if (selectedAggregateChanged) notifyAnySelected()
}

export function applyArticlePatches(patches) {
  const changedKeys = []
  const changedDates = new Set()
  let selectedAggregateChanged = false
  let selectedCountDelta = 0

  for (const { key, patch } of patches) {
    const current = articlesByKey.get(key)
    if (!current) continue

    const next = { ...current, ...patch }
    const date = parseArticleKey(key).date
    articlesByKey.set(key, next)
    changedKeys.push(key)

    const lifecycleChanged = (
      Boolean(current.removed) !== Boolean(next.removed)
      || Boolean(current.read?.isRead) !== Boolean(next.read?.isRead)
    )
    if (lifecycleChanged || 'summary' in patch) changedDates.add(date)

    if (current.selected || next.selected) selectedAggregateChanged = true
    if ('selected' in patch) {
      selectedCountDelta += (patch.selected ? 1 : 0) - (current.selected ? 1 : 0)
    }
  }

  if (selectedCountDelta !== 0) {
    auxiliary = { ...auxiliary, selectedCount: auxiliary.selectedCount + selectedCountDelta }
  }
  if (selectedAggregateChanged) recomputeSelectedArticles()

  changedKeys.forEach(notifyArticle)
  changedDates.forEach(notifyDay)
  if (selectedAggregateChanged) notifyAnySelected()
}

export function applyDayPatch(date, patch) {
  const current = daysByDate.get(date)
  if (!current) return
  daysByDate.set(date, { ...current, ...patch })
  notifyDay(date)
}

// ─── Subscriptions ───────────────────────────────────────────────────────────

function subscribeArticle(key, listener) {
  if (!articleListeners.has(key)) articleListeners.set(key, new Set())
  articleListeners.get(key).add(listener)
  return () => {
    const set = articleListeners.get(key)
    if (!set) return
    set.delete(listener)
    if (set.size === 0) articleListeners.delete(key)
  }
}

function subscribeDay(date, listener) {
  if (!dayListeners.has(date)) dayListeners.set(date, new Set())
  dayListeners.get(date).add(listener)
  return () => {
    const set = dayListeners.get(date)
    if (!set) return
    set.delete(listener)
    if (set.size === 0) dayListeners.delete(date)
  }
}

function subscribeFeed(listener) {
  feedListeners.add(listener)
  return () => feedListeners.delete(listener)
}

function subscribeContainerExpanded(containerId, listener) {
  if (!containerListeners.has(containerId)) containerListeners.set(containerId, new Set())
  containerListeners.get(containerId).add(listener)
  return () => {
    const set = containerListeners.get(containerId)
    if (!set) return
    set.delete(listener)
    if (set.size === 0) containerListeners.delete(containerId)
  }
}

function subscribeAnySelected(listener) {
  anySelectedListeners.add(listener)
  return () => anySelectedListeners.delete(listener)
}

// ─── Snapshots ───────────────────────────────────────────────────────────────

export function getSnapshotArticle(key) {
  return articlesByKey.get(key) ?? null
}

export function getSnapshotDay(date) {
  return daysByDate.get(date) ?? null
}

export function findArticleKeysByUrls(urls) {
  const urlSet = new Set(urls)
  const found = []
  for (const [key, slice] of articlesByKey) {
    if (urlSet.has(slice.url)) found.push(key)
  }
  return found
}

function getSnapshotFeed() {
  return feed
}

function getSnapshotVisibleDates() {
  return feed.visibleDates
}

function buildDayView(date) {
  const day = daysByDate.get(date)
  if (!day) return null

  const articles = day.articleKeys.map(key => articlesByKey.get(key)).filter(Boolean)
  const total = articles.length
  let removedCount = 0
  let completedCount = 0
  for (const article of articles) {
    if (article.removed) removedCount += 1
    if (article.removed || article.read?.isRead) completedCount += 1
  }

  const issuesWithStatus = day.issues.map(issue => {
    const issueArticles = articles.filter(article => article.category === issue.category)
    let issueRemoved = 0
    for (const article of issueArticles) {
      if (article.removed) issueRemoved += 1
    }
    return {
      ...issue,
      hasArticles: issueArticles.length > 0,
      allRemoved: issueArticles.length > 0 && issueRemoved === issueArticles.length,
    }
  })

  return {
    date: day.date,
    issues: issuesWithStatus,
    digest: day.digest,
    storage_updated_at: day.storage_updated_at,
    articleKeys: day.articleKeys,
    totalCount: total,
    removedCount,
    completedCount,
    allRemoved: total > 0 && removedCount === total,
  }
}

function getSnapshotDayView(date) {
  if (dayViewCache.has(date)) return dayViewCache.get(date)
  const view = buildDayView(date)
  if (view) dayViewCache.set(date, view)
  return view
}

function buildNewsletterView(date, sourceId) {
  const day = daysByDate.get(date)
  if (!day) return null
  const issue = day.issues.find(i => i.source_id === sourceId)
  if (!issue) return null

  const articles = day.articleKeys
    .map(key => articlesByKey.get(key))
    .filter(article => article && article.category === issue.category)

  if (articles.length === 0) return null

  const hasSections = articles.some(a => a.section)
  const sectionsByKey = new Map()
  if (hasSections) {
    for (const article of articles) {
      const sectionKey = article.section
      if (!sectionsByKey.has(sectionKey)) {
        sectionsByKey.set(sectionKey, {
          key: sectionKey,
          emoji: article.sectionEmoji,
          order: article.sectionOrder ?? 0,
          articles: [],
        })
      }
      sectionsByKey.get(sectionKey).articles.push(article)
    }
  }
  const sections = [...sectionsByKey.values()].sort((a, b) => a.order - b.order).map(section => {
    const sectionTotal = section.articles.length
    let sectionRemoved = 0
    let sectionCompleted = 0
    for (const article of section.articles) {
      if (article.removed) sectionRemoved += 1
      if (article.removed || article.read?.isRead) sectionCompleted += 1
    }
    return {
      key: section.key,
      emoji: section.emoji,
      order: section.order,
      articleKeys: section.articles.map(a => articleKey(date, a.url)),
      totalCount: sectionTotal,
      completedCount: sectionCompleted,
      allRemoved: sectionTotal > 0 && sectionRemoved === sectionTotal,
    }
  })

  const total = articles.length
  let removedCount = 0
  let completedCount = 0
  for (const article of articles) {
    if (article.removed) removedCount += 1
    if (article.removed || article.read?.isRead) completedCount += 1
  }

  return {
    date,
    sourceId,
    title: issue.category,
    subtitle: issue.subtitle,
    issue,
    articleKeys: articles.map(a => articleKey(date, a.url)),
    sections,
    hasSections,
    totalCount: total,
    completedCount,
    removedCount,
    allRemoved: total > 0 && removedCount === total,
  }
}

function getSnapshotNewsletterView(date, sourceId) {
  let perDate = newsletterViewCache.get(date)
  if (!perDate) {
    perDate = new Map()
    newsletterViewCache.set(date, perDate)
  }
  if (perDate.has(sourceId)) return perDate.get(sourceId)
  const view = buildNewsletterView(date, sourceId)
  perDate.set(sourceId, view)
  return view
}

function getSnapshotContainerExpanded(containerId) {
  return auxiliary.expandedContainerIds.has(containerId)
}

function getSnapshotAnySelected() {
  return auxiliary.selectedCount > 0
}

let selectedArticlesCache = []

function recomputeSelectedArticles() {
  const next = []
  for (const [key, slice] of articlesByKey) {
    if (!slice.selected) continue
    next.push({
      key,
      date: parseArticleKey(key).date,
      url: slice.url,
      title: slice.title,
      summary: slice.summary,
    })
  }
  selectedArticlesCache = next
}

function getSnapshotSelectedArticles() {
  return selectedArticlesCache
}

// ─── Selector hooks ──────────────────────────────────────────────────────────

export function useFeedStatus() {
  return useSyncExternalStore(subscribeFeed, getSnapshotFeed)
}

export function useVisibleDates() {
  return useSyncExternalStore(subscribeFeed, getSnapshotVisibleDates)
}

export function useArticleSlice(key) {
  return useSyncExternalStore(
    listener => subscribeArticle(key, listener),
    () => getSnapshotArticle(key)
  )
}

export function useDayView(date) {
  return useSyncExternalStore(
    listener => subscribeDay(date, listener),
    () => getSnapshotDayView(date)
  )
}

export function useNewsletterView(date, sourceId) {
  return useSyncExternalStore(
    listener => subscribeDay(date, listener),
    () => getSnapshotNewsletterView(date, sourceId)
  )
}

export function useDigestState(date) {
  return useSyncExternalStore(
    listener => subscribeDay(date, listener),
    () => daysByDate.get(date)?.digest ?? null
  )
}

export function useIsSelected(key) {
  return useSyncExternalStore(
    listener => subscribeArticle(key, listener),
    () => articlesByKey.get(key)?.selected ?? false
  )
}

export function useIsExpanded(containerId) {
  return useSyncExternalStore(
    listener => subscribeContainerExpanded(containerId, listener),
    () => getSnapshotContainerExpanded(containerId)
  )
}

export function useIsSelectMode() {
  return useSyncExternalStore(subscribeAnySelected, getSnapshotAnySelected)
}

export function useSelectedArticles() {
  return useSyncExternalStore(subscribeAnySelected, getSnapshotSelectedArticles)
}

// ─── Interaction ─────────────────────────────────────────────────────────────

function isArticleKeyDisabled(key) {
  return Boolean(articlesByKey.get(key)?.removed)
}

function getInteractionSnapshot() {
  const selectedIds = new Set()
  for (const [key, slice] of articlesByKey) {
    if (slice.selected) selectedIds.add(key)
  }
  return {
    selectedIds,
    expandedContainerIds: auxiliary.expandedContainerIds,
    suppressNextShortPress: auxiliary.suppressNextShortPress,
  }
}

function commitInteractionState(nextState) {
  const prevExpanded = auxiliary.expandedContainerIds
  const changedDates = new Set()

  for (const [key, slice] of articlesByKey) {
    const shouldBeSelected = nextState.selectedIds.has(key)
    if (slice.selected !== shouldBeSelected) {
      articlesByKey.set(key, { ...slice, selected: shouldBeSelected })
      notifyArticle(key)
      changedDates.add(parseArticleKey(key).date)
    }
  }

  const newSelectedCount = nextState.selectedIds.size
  const selectionChanged = newSelectedCount !== auxiliary.selectedCount
  const expandedChanged = nextState.expandedContainerIds !== prevExpanded

  auxiliary = {
    expandedContainerIds: nextState.expandedContainerIds,
    suppressNextShortPress: nextState.suppressNextShortPress,
    selectedCount: newSelectedCount,
  }

  if (selectionChanged) recomputeSelectedArticles()

  if (expandedChanged) {
    saveExpandedToStorage(nextState.expandedContainerIds)
    const allIds = new Set([...prevExpanded, ...nextState.expandedContainerIds])
    for (const id of allIds) {
      if (prevExpanded.has(id) !== nextState.expandedContainerIds.has(id)) {
        notifyContainer(id)
      }
    }
  }

  if (selectionChanged) notifyAnySelected()
}

export const interactionActions = Object.freeze({
  itemShortPress(itemId) {
    const snapshot = getInteractionSnapshot()
    const { state: nextState, decision } = interactionReduce(snapshot, { type: 'ITEM_SHORT_PRESS', itemId }, { isDisabled: isArticleKeyDisabled })
    commitInteractionState(nextState)
    return Boolean(decision?.shouldOpenItem)
  },
  itemLongPress(itemId) {
    const snapshot = getInteractionSnapshot()
    const { state: nextState } = interactionReduce(snapshot, { type: 'ITEM_LONG_PRESS', itemId }, { isDisabled: isArticleKeyDisabled })
    commitInteractionState(nextState)
  },
  containerShortPress(containerId) {
    const snapshot = getInteractionSnapshot()
    const { state: nextState } = interactionReduce(snapshot, { type: 'CONTAINER_SHORT_PRESS', containerId }, { isDisabled: isArticleKeyDisabled })
    commitInteractionState(nextState)
  },
  containerLongPress(containerId, childIds) {
    const snapshot = getInteractionSnapshot()
    const { state: nextState } = interactionReduce(snapshot, { type: 'CONTAINER_LONG_PRESS', containerId, childIds }, { isDisabled: isArticleKeyDisabled })
    commitInteractionState(nextState)
  },
  clearSelection() {
    const snapshot = getInteractionSnapshot()
    const { state: nextState } = interactionReduce(snapshot, { type: 'CLEAR_SELECTION' }, { isDisabled: isArticleKeyDisabled })
    commitInteractionState(nextState)
  },
  setExpanded(containerId, expanded) {
    const snapshot = getInteractionSnapshot()
    const { state: nextState } = interactionReduce(snapshot, { type: 'SET_EXPANDED', containerId, expanded }, { isDisabled: isArticleKeyDisabled })
    commitInteractionState(nextState)
  },
})

// ─── Summary actions ─────────────────────────────────────────────────────────

function dispatchSummaryEvent(key, event, extra = '') {
  const slice = articlesByKey.get(key)
  if (!slice) return

  const currentData = slice.summary
  const fromStatus = summaryDataReducer.getSummaryDataStatus(currentData)
  const { state: toStatus, patch } = summaryDataReducer.reduceSummaryData(currentData, event)

  if (fromStatus !== toStatus) {
    if (event.type === summaryDataReducer.SummaryDataEventType.SUMMARY_LOAD_SUCCEEDED) {
      logTransitionSuccess('summary-data', slice.url, toStatus, extra)
    } else {
      logTransition('summary-data', slice.url, fromStatus, toStatus, extra)
    }
  }

  if (!patch) return

  applyArticlePatch(key, {
    summary: { ...(currentData || {}), ...patch }
  })
}

function acquireSummaryExpand(key, url) {
  if (!acquireZenLock(url)) return false
  for (const [k, slice] of articlesByKey) {
    if (k !== key && slice.expandedView) {
      releaseZenLock(slice.url)
      applyArticlePatch(k, { expandedView: false })
      logTransition('summary-view', slice.url, 'expanded', 'collapsed', 'superseded')
    }
  }
  applyArticlePatch(key, { expandedView: true })
  return true
}

export const summaryActions = Object.freeze({
  fetch(key, effort) {
    const slice = articlesByKey.get(key)
    if (!slice) return
    const requestedEffort = effort ?? slice.summary?.effort ?? 'low'

    abortControllers.get(key)?.abort()
    const controller = new AbortController()
    abortControllers.set(key, controller)

    const token = createRequestToken()
    requestTokens.set(key, token)
    previousSummaryData.set(key, slice.summary ? { ...slice.summary } : null)

    dispatchSummaryEvent(key, {
      type: summaryDataReducer.SummaryDataEventType.SUMMARY_REQUESTED,
      effort: requestedEffort,
    }, `effort=${requestedEffort}`)

    const { url } = slice

    window.fetch('/api/summarize-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        summarize_effort: requestedEffort,
        issue_date: slice.issueDate,
      }),
      signal: controller.signal,
    }).then(r => r.json()).then(result => {
      if (requestTokens.get(key) !== token) return

      if (result.success) {
        dispatchSummaryEvent(key, {
          type: summaryDataReducer.SummaryDataEventType.SUMMARY_LOAD_SUCCEEDED,
          markdown: result.summary_markdown,
          effort: requestedEffort,
          checkedAt: new Date().toISOString(),
        })
        if (result.payload) {
          ingestDayPayload(result.payload)
        }
        const currentSlice = articlesByKey.get(key)
        emitToast({
          title: currentSlice?.title ?? url,
          url,
          onOpen: () => summaryActions.expand(key),
        })
      } else {
        dispatchSummaryEvent(key, {
          type: summaryDataReducer.SummaryDataEventType.SUMMARY_LOAD_FAILED,
          errorMessage: result.error,
        }, result.error)
      }
      requestTokens.delete(key)
      previousSummaryData.delete(key)
    }).catch(error => {
      if (error.name === 'AbortError') {
        if (requestTokens.get(key) === token) {
          dispatchSummaryEvent(key, {
            type: summaryDataReducer.SummaryDataEventType.SUMMARY_ROLLBACK,
            previousData: previousSummaryData.get(key),
          })
          requestTokens.delete(key)
        }
        return
      }
      dispatchSummaryEvent(key, {
        type: summaryDataReducer.SummaryDataEventType.SUMMARY_LOAD_FAILED,
        errorMessage: error.message,
      }, error.message)
      requestTokens.delete(key)
      previousSummaryData.delete(key)
      console.error(`Failed to fetch summary for ${url}:`, error)
    })
  },

  toggle(key, effort) {
    const slice = articlesByKey.get(key)
    if (!slice) return

    const status = summaryDataReducer.getSummaryDataStatus(slice.summary)
    const markdown = slice.summary?.markdown || ''
    const isAvailable = status === summaryDataReducer.SummaryDataStatus.AVAILABLE && markdown

    if (isAvailable) {
      if (slice.expandedView) {
        summaryActions.collapse(key)
      } else {
        if (acquireSummaryExpand(key, slice.url)) {
          logTransition('summary-view', slice.url, 'collapsed', 'expanded', 'tap')
        }
      }
    } else {
      summaryActions.fetch(key, effort)
    }
  },

  collapse(key) {
    const slice = articlesByKey.get(key)
    if (!slice) return
    logTransition('summary-view', slice.url, 'expanded', 'collapsed')
    releaseZenLock(slice.url)
    applyArticlePatch(key, { expandedView: false })
  },

  expand(key) {
    const slice = articlesByKey.get(key)
    if (!slice) return
    if (acquireSummaryExpand(key, slice.url)) {
      logTransition('summary-view', slice.url, 'collapsed', 'expanded', 'tap')
    }
  },

  abort(key) {
    abortControllers.get(key)?.abort()
    abortControllers.delete(key)
    requestTokens.delete(key)
    previousSummaryData.delete(key)
  },
})
