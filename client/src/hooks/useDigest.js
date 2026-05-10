import { useCallback, useEffect, useRef, useState } from 'react'
import { queueBatchArticlePatches, queueDailyPayloadPatch } from '../lib/dailyPayloadMutations'
import { createRequestToken } from '../lib/requestUtils'
import { logTransition } from '../lib/stateTransitionLogger'
import { acquireZenLock, releaseZenLock } from '../lib/zenLock'
import { ArticleLifecycleEventType, reduceArticleLifecycle } from '../reducers/articleLifecycleReducer'
import * as summaryDataReducer from '../reducers/summaryDataReducer'
import { getSnapshotArticle, getSnapshotDay, interactionActions, parseArticleKey, useDigestState, useVisibleDates } from '../store/articleStore'

const DIGEST_LOCK_OWNER = 'digest'

function pickTargetDate(selectedArticles) {
  if (selectedArticles.length === 0) return null
  return selectedArticles
    .map(({ key }) => parseArticleKey(key).date)
    .sort()
    .at(-1)
}

export function useDigest() {
  const visibleDates = useVisibleDates()
  const [expanded, setExpanded] = useState(false)
  const [targetDate, setTargetDate] = useState(null)
  const [triggering, setTriggering] = useState(false)
  const [pendingRequest, setPendingRequest] = useState(null)
  const abortControllerRef = useRef(null)
  const requestTokenRef = useRef(null)

  const latestVisibleDate = visibleDates.length > 0 ? visibleDates[visibleDates.length - 1] : null
  const activeDate = targetDate ?? latestVisibleDate ?? null
  const data = useDigestState(activeDate ?? '0000-00-00')

  const status = summaryDataReducer.getSummaryDataStatus(data)
  const markdown = data?.markdown || ''
  const articleUrls = data?.articleUrls || []
  const errorMessage = data?.errorMessage || null
  const isAvailable = status === summaryDataReducer.SummaryDataStatus.AVAILABLE && markdown
  const loading = triggering
  const isError = status === summaryDataReducer.SummaryDataStatus.ERROR
  const articleCount = articleUrls.length

  const groupKeysByDate = useCallback((selectedArticles) => {
    const grouped = new Map()
    for (const { key } of selectedArticles) {
      const { date } = parseArticleKey(key)
      if (!grouped.has(date)) grouped.set(date, [])
      grouped.get(date).push(key)
    }
    return grouped
  }, [])

  const updateArticlesAcrossDates = useCallback(async (keysByDate, buildPatch) => {
    const patches = []
    for (const [, keys] of keysByDate) {
      for (const key of keys) {
        const liveArticle = getSnapshotArticle(key)
        if (!liveArticle) continue
        patches.push({ key, buildPatch })
      }
    }
    await queueBatchArticlePatches(patches)
  }, [])

  const markDigestArticlesLoading = useCallback(async (keysByDate) => {
    const previousSummaryByKey = new Map()
    await updateArticlesAcrossDates(keysByDate, (article) => {
      const key = `${article.issueDate}::${article.url}`
      previousSummaryByKey.set(key, article.summary ?? null)
      return {
        summary: {
          ...(article.summary || {}),
          ...summaryDataReducer.reduceSummaryData(article.summary, {
            type: summaryDataReducer.SummaryDataEventType.SUMMARY_REQUESTED,
            effort: 'low',
          }).patch,
        },
      }
    })
    return previousSummaryByKey
  }, [updateArticlesAcrossDates])

  const restoreDigestArticlesSummary = useCallback(async (keysByDate, previousSummaryByKey) => {
    if (!previousSummaryByKey) return
    await updateArticlesAcrossDates(keysByDate, (article) => ({
      summary: previousSummaryByKey.get(`${article.issueDate}::${article.url}`) ?? null,
    }))
  }, [updateArticlesAcrossDates])

  const markDigestArticlesConsumed = useCallback(async (keysByDate, shouldRemove) => {
    const markedAt = new Date().toISOString()
    await updateArticlesAcrossDates(keysByDate, (article) => (
      shouldRemove
        ? reduceArticleLifecycle(article, { type: ArticleLifecycleEventType.MARK_REMOVED }).patch
        : reduceArticleLifecycle(article, { type: ArticleLifecycleEventType.MARK_READ, markedAt }).patch
    ))
  }, [updateArticlesAcrossDates])

  const writeDigest = useCallback((digestPatch) => {
    const date = activeDate
    if (!date) return Promise.resolve(null)

    const daySnapshot = getSnapshotDay(date)
    if (!daySnapshot) return Promise.resolve(null)

    const nextDigest = { ...(daySnapshot.digest || {}), ...digestPatch }
    const fromStatus = summaryDataReducer.getSummaryDataStatus(daySnapshot.digest)
    const toStatus = summaryDataReducer.getSummaryDataStatus(nextDigest)
    if (fromStatus !== toStatus) {
      logTransition('digest', DIGEST_LOCK_OWNER, fromStatus, toStatus)
    }

    return queueDailyPayloadPatch({
      date,
      payloadPatch: { digest: nextDigest },
    }).catch((error) => {
      console.error(`Failed to update digest for ${date}:`, error)
      throw error
    })
  }, [activeDate])

  const trigger = (selectedArticles) => {
    if (!selectedArticles || selectedArticles.length < 2) return

    if (isAvailable && data?.articleKeys) {
      const incomingKeys = new Set(selectedArticles.map(d => d.key))
      const cachedKeys = new Set(data.articleKeys)
      if (incomingKeys.size === cachedKeys.size && [...incomingKeys].every(k => cachedKeys.has(k))) {
        expand()
        return
      }
    }

    const date = pickTargetDate(selectedArticles)
    if (!date) return

    const requestToken = createRequestToken()
    requestTokenRef.current = requestToken

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setPendingRequest({ selectedArticles, date, requestToken })
    setTargetDate(date)
    setTriggering(true)
  }

  const expand = useCallback(() => {
    if (acquireZenLock(DIGEST_LOCK_OWNER)) {
      logTransition('digest-view', DIGEST_LOCK_OWNER, 'collapsed', 'expanded', 'tap')
      setExpanded(true)
    }
  }, [])

  useEffect(() => {
    if (!pendingRequest) return
    if (targetDate !== pendingRequest.date) return

    const { selectedArticles, requestToken } = pendingRequest
    const keysByDate = groupKeysByDate(selectedArticles)
    const articleDescriptors = selectedArticles.map(({ url, title }) => ({ url, title }))
    const articleUrls = selectedArticles.map(d => d.url)
    const controller = new AbortController()
    abortControllerRef.current = controller
    setPendingRequest(null)

    const runDigest = async () => {
      let previousSummaryByKey
      try {
        previousSummaryByKey = await markDigestArticlesLoading(keysByDate)
        void writeDigest({ errorMessage: null })

        const response = await window.fetch('/api/digest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ articles: articleDescriptors, effort: 'low' }),
          signal: controller.signal,
        })

        const result = await response.json()

        if (requestTokenRef.current !== requestToken) return

        if (result.success) {
          await restoreDigestArticlesSummary(keysByDate, previousSummaryByKey)
          const includedUrls = new Set(result.included_urls ?? articleUrls)
          const includedKeys = selectedArticles
            .filter(({ url }) => includedUrls.has(url))
            .map(({ key }) => key)
          await writeDigest({
            status: summaryDataReducer.SummaryDataStatus.AVAILABLE,
            markdown: result.digest_markdown,
            articleKeys: includedKeys,
            articleUrls: [...includedUrls],
            generatedAt: new Date().toISOString(),
            effort: 'low',
            errorMessage: null,
          })
          interactionActions.clearSelection()
          expand()
          return
        }

        await writeDigest({
          status: summaryDataReducer.SummaryDataStatus.ERROR,
          errorMessage: result.error,
        })
      } catch (error) {
        if (error.name === 'AbortError') {
          await restoreDigestArticlesSummary(keysByDate, previousSummaryByKey)
          return
        }
        await restoreDigestArticlesSummary(keysByDate, previousSummaryByKey)
        await writeDigest({
          status: summaryDataReducer.SummaryDataStatus.ERROR,
          errorMessage: error.message,
        })
      } finally {
        if (requestTokenRef.current === requestToken) {
          requestTokenRef.current = null
          setTriggering(false)
        }
      }
    }

    void runDigest()
  }, [pendingRequest, targetDate, expand, markDigestArticlesLoading, restoreDigestArticlesSummary, writeDigest, groupKeysByDate])

  useEffect(() => {
    if (status !== summaryDataReducer.SummaryDataStatus.LOADING) return
    void writeDigest({
      status: summaryDataReducer.SummaryDataStatus.UNKNOWN,
      errorMessage: null,
    })
  }, [status, writeDigest])

  const collapse = useCallback(async (shouldRemove = false) => {
    try {
      if (status === summaryDataReducer.SummaryDataStatus.AVAILABLE && data?.articleKeys?.length > 0) {
        const keysByDate = new Map()
        for (const key of data.articleKeys) {
          const { date } = parseArticleKey(key)
          if (!keysByDate.has(date)) keysByDate.set(date, [])
          keysByDate.get(date).push(key)
        }
        await markDigestArticlesConsumed(keysByDate, shouldRemove)
      }
    } catch (error) {
      console.error(`Failed to persist digest consumed lifecycle: ${error.message}`)
    } finally {
      logTransition('digest-view', DIGEST_LOCK_OWNER, 'expanded', 'collapsed')
      releaseZenLock(DIGEST_LOCK_OWNER)
      setExpanded(false)
    }
  }, [status, data, markDigestArticlesConsumed])

  useEffect(() => {
    return () => {
      releaseZenLock(DIGEST_LOCK_OWNER)
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  return {
    data,
    status,
    markdown,
    articleUrls,
    errorMessage,
    loading,
    expanded,
    articleCount,
    isAvailable,
    isError,
    trigger,
    collapse,
    expand,
  }
}
