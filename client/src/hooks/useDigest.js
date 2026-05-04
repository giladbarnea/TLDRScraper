import { useCallback, useEffect, useRef, useState } from 'react'
import { queueBatchArticlePatches, queueDailyPayloadPatch } from '../lib/dailyPayloadMutations'
import { createRequestToken } from '../lib/requestUtils'
import { logTransition } from '../lib/stateTransitionLogger'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import { acquireZenLock, releaseZenLock } from '../lib/zenLock'
import { ArticleLifecycleEventType, reduceArticleLifecycle } from '../reducers/articleLifecycleReducer'
import * as summaryDataReducer from '../reducers/summaryDataReducer'
import { getSnapshotArticle, getSnapshotArticleByUrl, getSnapshotDay, interactionActions, useDaySlice } from '../store/articleStore'

const DIGEST_LOCK_OWNER = 'digest'

function findMostRecentDate(articleDescriptors, payloads) {
  const urlSet = new Set(articleDescriptors.map(d => d.url))
  const matchingDates = payloads
    .filter(p => p.articles.some(a => urlSet.has(a.url)))
    .map(p => p.date)
  return matchingDates.sort().at(-1)
}

export function useDigest(results) {
  const [expanded, setExpanded] = useState(false)
  const [targetDate, setTargetDate] = useState(null)
  const [triggering, setTriggering] = useState(false)
  const [pendingRequest, setPendingRequest] = useState(null)
  const abortControllerRef = useRef(null)
  const requestTokenRef = useRef(null)

  const latestPayloadDate = results?.payloads
    ? [...results.payloads].sort((a, b) => b.date.localeCompare(a.date))[0]?.date
    : null

  const activeDate = targetDate ?? latestPayloadDate ?? null
  const daySlice = useDaySlice(activeDate ?? '0000-00-00')

  const data = daySlice?.digest || null
  const status = summaryDataReducer.getSummaryDataStatus(data)
  const markdown = data?.markdown || ''
  const articleUrls = data?.articleUrls || []
  const errorMessage = data?.errorMessage || null
  const isAvailable = status === summaryDataReducer.SummaryDataStatus.AVAILABLE && markdown
  const loading = triggering
  const isError = status === summaryDataReducer.SummaryDataStatus.ERROR
  const articleCount = articleUrls.length

  const groupDescriptorsByDate = useCallback((articleDescriptors) => {
    const grouped = new Map()
    for (const descriptor of articleDescriptors) {
      const article = getSnapshotArticleByUrl(descriptor.url)
      const date = article?.issueDate
      if (!date) continue
      if (!grouped.has(date)) grouped.set(date, [])
      grouped.get(date).push(descriptor.url)
    }
    return grouped
  }, [])

  const updateArticlesAcrossDates = useCallback(async (urlsByDate, buildPatch) => {
    const patches = []
    for (const [date, urls] of urlsByDate) {
      const storageKey = getNewsletterScrapeKey(date)
      for (const url of urls) {
        const liveArticle = getSnapshotArticle(`${date}::${url}`)
        if (!liveArticle) continue
        patches.push({ date, url, buildPatch, storageKey })
      }
    }
    await queueBatchArticlePatches(patches)
  }, [])

  const markDigestArticlesLoading = useCallback(async (urlsByDate) => {
    const previousSummaryByUrl = new Map()
    await updateArticlesAcrossDates(urlsByDate, (article) => {
      previousSummaryByUrl.set(article.url, article.summary ?? null)
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
    return previousSummaryByUrl
  }, [updateArticlesAcrossDates])

  const restoreDigestArticlesSummary = useCallback(async (urlsByDate, previousSummaryByUrl) => {
    if (!previousSummaryByUrl) return
    await updateArticlesAcrossDates(urlsByDate, (article) => ({
      summary: previousSummaryByUrl.get(article.url) ?? null,
    }))
  }, [updateArticlesAcrossDates])

  const markDigestArticlesConsumed = useCallback(async (urlsByDate, shouldRemove) => {
    const markedAt = new Date().toISOString()
    await updateArticlesAcrossDates(urlsByDate, (article) => (
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

    const nextDigest = {
      ...(daySnapshot.digest || {}),
      ...digestPatch,
    }
    const fromStatus = summaryDataReducer.getSummaryDataStatus(daySnapshot.digest)
    const toStatus = summaryDataReducer.getSummaryDataStatus(nextDigest)
    if (fromStatus !== toStatus) {
      logTransition('digest', DIGEST_LOCK_OWNER, fromStatus, toStatus)
    }

    return queueDailyPayloadPatch({
      date,
      payloadPatch: { digest: nextDigest },
      previousPayload: null,
      storageKey: getNewsletterScrapeKey(date),
    }).catch((error) => {
      console.error(`Failed to update digest for ${date}:`, error)
      throw error
    })
  }, [activeDate])

  const trigger = (articleDescriptors) => {
    const payloads = results?.payloads
    if (!payloads || payloads.length === 0) return
    if (!articleDescriptors || articleDescriptors.length < 2) return

    if (isAvailable && data?.articleUrls) {
      const incomingUrls = new Set(articleDescriptors.map(d => d.url))
      const cachedUrls = new Set(data.articleUrls)
      if (incomingUrls.size === cachedUrls.size && [...incomingUrls].every(u => cachedUrls.has(u))) {
        expand()
        return
      }
    }

    const date = findMostRecentDate(articleDescriptors, payloads)
    if (!date) return

    const requestToken = createRequestToken()
    requestTokenRef.current = requestToken

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setPendingRequest({ articleDescriptors, date, requestToken })
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
    if (!daySlice || daySlice.date !== pendingRequest.date) return

    const { articleDescriptors, requestToken } = pendingRequest
    const urlsByDate = groupDescriptorsByDate(articleDescriptors)
    const articleUrls = articleDescriptors.map(d => d.url)
    const controller = new AbortController()
    abortControllerRef.current = controller
    setPendingRequest(null)

    const runDigest = async () => {
      let previousSummaryByUrl
      try {
        previousSummaryByUrl = await markDigestArticlesLoading(urlsByDate)
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
          await restoreDigestArticlesSummary(urlsByDate, previousSummaryByUrl)
          await writeDigest({
            status: summaryDataReducer.SummaryDataStatus.AVAILABLE,
            markdown: result.digest_markdown,
            articleUrls: result.included_urls ?? articleUrls,
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
          await restoreDigestArticlesSummary(urlsByDate, previousSummaryByUrl)
          return
        }
        await restoreDigestArticlesSummary(urlsByDate, previousSummaryByUrl)
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
  }, [pendingRequest, daySlice, targetDate, expand, markDigestArticlesLoading, restoreDigestArticlesSummary, writeDigest, groupDescriptorsByDate])

  useEffect(() => {
    if (status !== summaryDataReducer.SummaryDataStatus.LOADING) return
    void writeDigest({
      status: summaryDataReducer.SummaryDataStatus.UNKNOWN,
      errorMessage: null,
    })
  }, [status, writeDigest])

  const collapse = useCallback(async (shouldRemove = false) => {
    try {
      if (status === summaryDataReducer.SummaryDataStatus.AVAILABLE && data?.articleUrls?.length > 0) {
        const urlsByDate = groupDescriptorsByDate(
          data.articleUrls.map((url) => ({ url }))
        )
        await markDigestArticlesConsumed(urlsByDate, shouldRemove)
      }
    } catch (error) {
      console.error(`Failed to persist digest consumed lifecycle: ${error.message}`)
    } finally {
      logTransition('digest-view', DIGEST_LOCK_OWNER, 'expanded', 'collapsed')
      releaseZenLock(DIGEST_LOCK_OWNER)
      setExpanded(false)
    }
  }, [status, data, markDigestArticlesConsumed, groupDescriptorsByDate])

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
