import { useSyncExternalStore } from 'react'
import { mergePreservingLocalState } from '../lib/feedMerge'
import { createRequestToken } from '../lib/requestUtils'
import { logTransition, logTransitionSuccess } from '../lib/stateTransitionLogger'
import { emitToast } from '../lib/toastBus'
import { acquireZenLock, releaseZenLock } from '../lib/zenLock'
import { interactionReduce } from '../reducers/interactionReducer'
import * as summaryDataReducer from '../reducers/summaryDataReducer'

// ─── Storage ─────────────────────────────────────────────────────────────────

const articleSlices = new Map()  // key: `${date}::${url}`
const daySlices = new Map()      // key: date string
const hydratedDates = new Set()
const urlToArticleKey = new Map() // url → most-recent articleKey (for O(1) selection lookup)

// ─── Listeners ───────────────────────────────────────────────────────────────

const articleListeners = new Map()    // articleKey → Set<() => void>
const dayListeners = new Map()        // date → Set<() => void>
const dayArticleSummaryListeners = new Map() // date → Set<() => void>
const dayLifecycleListeners = new Map() // date → Set<() => void>
const containerListeners = new Map()  // containerId → Set<() => void>
const anySelectedListeners = new Set()

function notifyArticle(articleKey) {
  articleListeners.get(articleKey)?.forEach(listener => {
    listener()
  })
}

function notifyDay(date) {
  dayListeners.get(date)?.forEach(listener => {
    listener()
  })
}

function notifyDayArticleSummary(date) {
  dayArticleSummaryListeners.get(date)?.forEach(listener => {
    listener()
  })
}

function notifyDayLifecycle(date) {
  dayLifecycleListeners.get(date)?.forEach(listener => {
    listener()
  })
}

function notifyContainer(containerId) {
  containerListeners.get(containerId)?.forEach(listener => {
    listener()
  })
}

function notifyAnySelected() {
  // biome-ignore lint/suspicious/useIterableCallbackReturn: listeners are () => void.
  anySelectedListeners.forEach(listener => listener())
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

const abortControllers = new Map()   // articleKey → AbortController
const requestTokens = new Map()      // articleKey → token string
const previousSummaryData = new Map() // articleKey → previous summary snapshot

// ─── Derived day article summaries ──────────────────────────────────────────

const emptyDayArticlesSummary = Object.freeze({ allRemoved: false })
const dayArticleSummaries = new Map()

// ─── Helpers ─────────────────────────────────────────────────────────────────

function articleKey(date, url) {
  return `${date}::${url}`
}

function parseArticleKey(key) {
  const sep = key.indexOf('::')
  return { date: key.slice(0, sep), url: key.slice(sep + 2) }
}

function getArticleIdUrl(id) {
  return id.startsWith('article-') ? id.slice('article-'.length) : null
}

function isArticleIdDisabled(id) {
  const url = getArticleIdUrl(id)
  if (!url) return false
  const key = urlToArticleKey.get(url)
  if (!key) return false
  return Boolean(articleSlices.get(key)?.removed)
}

// Reconstruct a full payload object from store state (used by mutation layer)
export function composePayloadFromStore(date) {
  const daySlice = daySlices.get(date)
  if (!daySlice) return null

  const articles = []
  for (const [key, slice] of articleSlices) {
    const { date: sliceDate } = parseArticleKey(key)
    if (sliceDate !== date) continue
    articles.push(sliceToArticle(slice))
  }
  articles.sort((a, b) => (a.originalOrder ?? 0) - (b.originalOrder ?? 0))

  return { ...daySlice, articles }
}

function sliceToArticle(slice) {
  const { expandedView, selected, originalOrder, ...articleFields } = slice
  return { originalOrder, ...articleFields }
}

// ─── Hydration ───────────────────────────────────────────────────────────────

export function hydrateDay(date, payload) {
  if (hydratedDates.has(date)) {
    mergeDayFromServer(date, payload)
    return
  }
  hydratedDates.add(date)
  ingestPayload(date, payload, false)
}

export function mergeDayFromServer(date, freshPayload) {
  const localPayload = composePayloadFromStore(date)
  const merged = localPayload
    ? mergePreservingLocalState(freshPayload, localPayload)
    : freshPayload

  ingestPayload(date, merged, true)
}

function ingestPayload(date, payload, notifyListeners) {
  const changedArticleKeys = []
  const nextArticleKeys = new Set()
  let selectedAggregateChanged = false
  let dayLifecycleChanged = false

  payload.articles.forEach((article, index) => {
    const key = articleKey(date, article.url)
    nextArticleKeys.add(key)
    const existing = articleSlices.get(key)
    const next = {
      ...article,
      issueDate: date,  // authoritative stamp (GOTCHA 2026-02-15)
      originalOrder: index,
      expandedView: existing?.expandedView ?? false,
      selected: existing?.selected ?? false,
    }
    articleSlices.set(key, next)
    urlToArticleKey.set(article.url, key)
    if (next.selected) selectedAggregateChanged = true
    if (notifyListeners) {
      changedArticleKeys.push(key)
      if (
        Boolean(existing?.removed) !== Boolean(next.removed)
        || Boolean(existing?.read?.isRead) !== Boolean(next.read?.isRead)
      ) {
        dayLifecycleChanged = true
      }
    }
  })

  const { staleArticleKeys, staleSelectedCount } = deleteStaleArticles(date, nextArticleKeys)
  const dayArticleSummaryChanged = replaceDayArticleSummary(date, payload.articles)

  const nextDaySlice = {
    date,
    digest: payload.digest ?? null,
    issues: payload.issues ?? [],
    storage_updated_at: payload.storage_updated_at ?? null,
  }
  daySlices.set(date, nextDaySlice)

  if (selectedAggregateChanged || staleSelectedCount > 0) {
    auxiliary = { ...auxiliary, selectedCount: auxiliary.selectedCount - staleSelectedCount }
    recomputeSelectedDescriptors()
  }

  if (notifyListeners) {
    changedArticleKeys.forEach(notifyArticle)
    if (dayArticleSummaryChanged) notifyDayArticleSummary(date)
    if (dayLifecycleChanged) notifyDayLifecycle(date)
    notifyDay(date)
    if (selectedAggregateChanged || staleSelectedCount > 0) notifyAnySelected()
    staleArticleKeys.forEach(notifyArticle)
  }
}

function deleteStaleArticles(date, nextArticleKeys) {
  const staleArticleKeys = []
  let staleSelectedCount = 0

  for (const [key, slice] of articleSlices) {
    if (parseArticleKey(key).date !== date) continue
    if (nextArticleKeys.has(key)) continue

    articleSlices.delete(key)
    if (urlToArticleKey.get(slice.url) === key) urlToArticleKey.delete(slice.url)
    abortControllers.get(key)?.abort()
    abortControllers.delete(key)
    requestTokens.delete(key)
    previousSummaryData.delete(key)

    if (slice.selected) staleSelectedCount += 1
    staleArticleKeys.push(key)
  }

  return { staleArticleKeys, staleSelectedCount }
}

function buildDayArticlesSummary(total, removedCount) {
  return { allRemoved: total > 0 && removedCount === total }
}

function replaceDayArticleSummary(date, articles) {
  const previous = dayArticleSummaries.get(date)
  const total = articles.length
  const removedCount = articles.reduce((count, article) => count + (article.removed ? 1 : 0), 0)
  const nextSnapshot = buildDayArticlesSummary(total, removedCount)
  const snapshot = previous?.snapshot?.allRemoved === nextSnapshot.allRemoved
    ? previous.snapshot
    : nextSnapshot

  dayArticleSummaries.set(date, { total, removedCount, snapshot })
  return Boolean(previous && previous.snapshot !== snapshot)
}

function updateDayRemovedCount(date, currentRemoved, nextRemoved) {
  if (currentRemoved === nextRemoved) return false

  const previous = dayArticleSummaries.get(date)
  if (!previous) return false

  const removedDelta = (nextRemoved ? 1 : 0) - (currentRemoved ? 1 : 0)
  const removedCount = previous.removedCount + removedDelta
  const nextSnapshot = buildDayArticlesSummary(previous.total, removedCount)
  const snapshot = previous.snapshot.allRemoved === nextSnapshot.allRemoved
    ? previous.snapshot
    : nextSnapshot

  dayArticleSummaries.set(date, {
    total: previous.total,
    removedCount,
    snapshot,
  })

  return previous.snapshot !== snapshot
}

// ─── Write actions ────────────────────────────────────────────────────────────

export function applyArticlePatch(key, patch) {
  const current = articleSlices.get(key)
  if (!current) return
  const next = { ...current, ...patch }
  articleSlices.set(key, next)

  const date = parseArticleKey(key).date
  const selectedAggregateChanged = current.selected || next.selected
  const dayArticleSummaryChanged = updateDayRemovedCount(date, Boolean(current.removed), Boolean(next.removed))
  const dayLifecycleChanged = (
    Boolean(current.removed) !== Boolean(next.removed)
    || Boolean(current.read?.isRead) !== Boolean(next.read?.isRead)
  )

  if ('selected' in patch) {
    const selectedCountDelta = (patch.selected ? 1 : 0) - (current.selected ? 1 : 0)
    if (selectedCountDelta !== 0) {
      auxiliary = { ...auxiliary, selectedCount: auxiliary.selectedCount + selectedCountDelta }
    }
  }

  if (selectedAggregateChanged) recomputeSelectedDescriptors()

  notifyArticle(key)
  if (dayArticleSummaryChanged) notifyDayArticleSummary(date)
  if (dayLifecycleChanged) notifyDayLifecycle(date)
  if (selectedAggregateChanged) notifyAnySelected()
}

export function applyArticlePatches(patches) {
  const changedArticleKeys = []
  const changedDaySummaries = new Set()
  const changedDayLifecycles = new Set()
  let selectedAggregateChanged = false
  let selectedCountDelta = 0

  for (const { key, patch } of patches) {
    const current = articleSlices.get(key)
    if (!current) continue

    const next = { ...current, ...patch }
    const date = parseArticleKey(key).date
    articleSlices.set(key, next)
    changedArticleKeys.push(key)

    if (updateDayRemovedCount(date, Boolean(current.removed), Boolean(next.removed))) {
      changedDaySummaries.add(date)
    }

    if (
      Boolean(current.removed) !== Boolean(next.removed)
      || Boolean(current.read?.isRead) !== Boolean(next.read?.isRead)
    ) {
      changedDayLifecycles.add(date)
    }

    if (current.selected || next.selected) selectedAggregateChanged = true

    if ('selected' in patch) {
      selectedCountDelta += (patch.selected ? 1 : 0) - (current.selected ? 1 : 0)
    }
  }

  if (selectedCountDelta !== 0) {
    auxiliary = { ...auxiliary, selectedCount: auxiliary.selectedCount + selectedCountDelta }
  }
  if (selectedAggregateChanged) recomputeSelectedDescriptors()

  changedArticleKeys.forEach(notifyArticle)
  changedDaySummaries.forEach(notifyDayArticleSummary)
  changedDayLifecycles.forEach(notifyDayLifecycle)
  if (selectedAggregateChanged) notifyAnySelected()
}

export function applyDayPatch(date, patch) {
  const current = daySlices.get(date)
  if (!current) return
  daySlices.set(date, { ...current, ...patch })
  notifyDay(date)
}

export function replaceDayFromServer(date, freshPayload) {
  const localPayload = composePayloadFromStore(date)
  const merged = localPayload
    ? mergePreservingLocalState(freshPayload, localPayload)
    : freshPayload
  ingestPayload(date, merged, true)
}

// ─── Subscriptions ────────────────────────────────────────────────────────────

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

function subscribeDayArticleSummary(date, listener) {
  if (!dayArticleSummaryListeners.has(date)) dayArticleSummaryListeners.set(date, new Set())
  dayArticleSummaryListeners.get(date).add(listener)
  return () => {
    const set = dayArticleSummaryListeners.get(date)
    if (!set) return
    set.delete(listener)
    if (set.size === 0) dayArticleSummaryListeners.delete(date)
  }
}

function subscribeDayLifecycle(date, listener) {
  if (!dayLifecycleListeners.has(date)) dayLifecycleListeners.set(date, new Set())
  dayLifecycleListeners.get(date).add(listener)
  return () => {
    const set = dayLifecycleListeners.get(date)
    if (!set) return
    set.delete(listener)
    if (set.size === 0) dayLifecycleListeners.delete(date)
  }
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

// ─── Snapshots ────────────────────────────────────────────────────────────────

export function getSnapshotArticle(key) {
  return articleSlices.get(key) ?? null
}

export function getSnapshotArticleByUrl(url) {
  const key = urlToArticleKey.get(url)
  if (!key) return null
  return articleSlices.get(key) ?? null
}

export function getSnapshotDay(date) {
  return daySlices.get(date) ?? null
}

function getSnapshotContainerExpanded(containerId) {
  return auxiliary.expandedContainerIds.has(containerId)
}

function getSnapshotAnySelected() {
  return auxiliary.selectedCount > 0
}

let selectedDescriptorsCache = []

function recomputeSelectedDescriptors() {
  const next = []
  for (const [key, slice] of articleSlices) {
    if (!slice.selected) continue
    next.push({ url: slice.url, title: slice.title, date: parseArticleKey(key).date, summary: slice.summary })
  }
  selectedDescriptorsCache = next
}

function getSnapshotSelectedDescriptors() {
  return selectedDescriptorsCache
}

function getSnapshotDayArticlesSummary(date) {
  return dayArticleSummaries.get(date)?.snapshot ?? emptyDayArticlesSummary
}

// ─── Selector hooks ───────────────────────────────────────────────────────────

export function useArticleSlice(date, url) {
  const key = articleKey(date, url)
  return useSyncExternalStore(
    listener => subscribeArticle(key, listener),
    () => getSnapshotArticle(key)
  )
}

export function useDaySlice(date) {
  return useSyncExternalStore(
    listener => subscribeDay(date, listener),
    () => getSnapshotDay(date)
  )
}

export function useDayArticlesSummary(date) {
  return useSyncExternalStore(
    listener => subscribeDayArticleSummary(date, listener),
    () => getSnapshotDayArticlesSummary(date)
  )
}

function countCompletedArticles(date, urls) {
  return urls.reduce((count, url) => {
    const article = articleSlices.get(articleKey(date, url))
    return count + (article?.read?.isRead || article?.removed ? 1 : 0)
  }, 0)
}

function areAllArticlesRemoved(date, urls) {
  return urls.length > 0 && urls.every((url) => articleSlices.get(articleKey(date, url))?.removed)
}

export function useCompletedArticlesCount(date, urls) {
  return useSyncExternalStore(
    listener => subscribeDayLifecycle(date, listener),
    () => countCompletedArticles(date, urls)
  )
}

export function useAllArticlesRemoved(date, urls) {
  return useSyncExternalStore(
    listener => subscribeDayLifecycle(date, listener),
    () => areAllArticlesRemoved(date, urls)
  )
}

export function useIsSelected(id) {
  const url = getArticleIdUrl(id)
  const key = url ? urlToArticleKey.get(url) : null
  return useSyncExternalStore(
    listener => key ? subscribeArticle(key, listener) : () => {},
    () => key ? articleSlices.get(key)?.selected ?? false : false
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

export function useSelectedDescriptors() {
  return useSyncExternalStore(subscribeAnySelected, getSnapshotSelectedDescriptors)
}

// ─── Interaction ──────────────────────────────────────────────────────────────

function getInteractionSnapshot() {
  const selectedIds = new Set()
  for (const slice of articleSlices.values()) {
    const id = `article-${slice.url}`
    if (slice.selected) selectedIds.add(id)
  }
  return {
    selectedIds,
    expandedContainerIds: auxiliary.expandedContainerIds,
    suppressNextShortPress: auxiliary.suppressNextShortPress,
  }
}

function commitInteractionState(nextState) {
  const prevExpanded = auxiliary.expandedContainerIds

  // Update article selected flags
  for (const [key, slice] of articleSlices) {
    const id = `article-${slice.url}`
    const shouldBeSelected = nextState.selectedIds.has(id)
    if (slice.selected !== shouldBeSelected) {
      articleSlices.set(key, { ...slice, selected: shouldBeSelected })
      notifyArticle(key)
    }
  }

  const newSelectedCount = nextState.selectedIds.size
  const selectionChanged = newSelectedCount !== auxiliary.selectedCount

  // Update auxiliary
  const expandedChanged = nextState.expandedContainerIds !== prevExpanded
  auxiliary = {
    expandedContainerIds: nextState.expandedContainerIds,
    suppressNextShortPress: nextState.suppressNextShortPress,
    selectedCount: newSelectedCount,
  }

  if (selectionChanged) recomputeSelectedDescriptors()

  if (expandedChanged) {
    saveExpandedToStorage(nextState.expandedContainerIds)
    // Notify all container listeners
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
    const { state: nextState, decision } = interactionReduce(snapshot, { type: 'ITEM_SHORT_PRESS', itemId }, { isDisabled: isArticleIdDisabled })
    commitInteractionState(nextState)
    return Boolean(decision?.shouldOpenItem)
  },
  itemLongPress(itemId) {
    const snapshot = getInteractionSnapshot()
    const { state: nextState } = interactionReduce(snapshot, { type: 'ITEM_LONG_PRESS', itemId }, { isDisabled: isArticleIdDisabled })
    commitInteractionState(nextState)
  },
  containerShortPress(containerId) {
    const snapshot = getInteractionSnapshot()
    const { state: nextState } = interactionReduce(snapshot, { type: 'CONTAINER_SHORT_PRESS', containerId }, { isDisabled: isArticleIdDisabled })
    commitInteractionState(nextState)
  },
  containerLongPress(containerId, childIds) {
    const snapshot = getInteractionSnapshot()
    const { state: nextState } = interactionReduce(snapshot, { type: 'CONTAINER_LONG_PRESS', containerId, childIds }, { isDisabled: isArticleIdDisabled })
    commitInteractionState(nextState)
  },
  clearSelection() {
    const snapshot = getInteractionSnapshot()
    const { state: nextState } = interactionReduce(snapshot, { type: 'CLEAR_SELECTION' }, { isDisabled: isArticleIdDisabled })
    commitInteractionState(nextState)
  },
  setExpanded(containerId, expanded) {
    const snapshot = getInteractionSnapshot()
    const { state: nextState } = interactionReduce(snapshot, { type: 'SET_EXPANDED', containerId, expanded }, { isDisabled: isArticleIdDisabled })
    commitInteractionState(nextState)
  },
})

// ─── Summary actions ──────────────────────────────────────────────────────────

function dispatchSummaryEvent(key, event, extra = '') {
  const slice = articleSlices.get(key)
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

// Expand at most one summary at a time; zenLock coordinates with digest overlay
function acquireSummaryExpand(key, url) {
  if (!acquireZenLock(url)) return false
  for (const [k, slice] of articleSlices) {
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
    const slice = articleSlices.get(key)
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
      body: JSON.stringify({ url, summarize_effort: requestedEffort }),
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
        const currentSlice = articleSlices.get(key)
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
    const slice = articleSlices.get(key)
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
    const slice = articleSlices.get(key)
    if (!slice) return
    logTransition('summary-view', slice.url, 'expanded', 'collapsed')
    releaseZenLock(slice.url)
    applyArticlePatch(key, { expandedView: false })
  },

  expand(key) {
    const slice = articleSlices.get(key)
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
