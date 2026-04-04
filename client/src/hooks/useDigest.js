import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useInteraction } from '../contexts/InteractionContext'
import { logTransition } from '../lib/stateTransitionLogger'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import { ArticleLifecycleEventType, reduceArticleLifecycle } from '../reducers/articleLifecycleReducer'
import * as summaryDataReducer from '../reducers/summaryDataReducer'
import { acquireZenLock, releaseZenLock } from './useSummary'
import { getCachedStorageValue, setStorageValueAsync, useSupabaseStorage } from './useSupabaseStorage'

const DIGEST_LOCK_OWNER = 'digest'

function findMostRecentDate(articleDescriptors, payloads) {
  const urlSet = new Set(articleDescriptors.map(d => d.url))
  const matchingDates = payloads
    .filter(p => p.articles.some(a => urlSet.has(a.url)))
    .map(p => p.date)
  return matchingDates.sort().at(-1)
}

export function useDigest(results) {
  const { clearSelection } = useInteraction()
  const [expanded, setExpanded] = useState(false)
  const [targetDate, setTargetDate] = useState(null)
  const [triggering, setTriggering] = useState(false)
  const [pendingRequest, setPendingRequest] = useState(null)
  const abortControllerRef = useRef(null)
  const requestTokenRef = useRef(null)

  const latestPayloadDate = results?.payloads
    ? [...results.payloads].sort((a, b) => b.date.localeCompare(a.date))[0]?.date
    : null
  const storageKey = getNewsletterScrapeKey(targetDate ?? latestPayloadDate ?? '0000-00-00')
  const [payload, setPayload] = useSupabaseStorage(storageKey, null)
  const setPayloadRef = useRef(null)
  setPayloadRef.current = setPayload

  const activePayload = payload

  const data = activePayload?.digest || null
  const status = summaryDataReducer.getSummaryDataStatus(data)
  const markdown = data?.markdown || ''

  const html = (() => {
    if (!markdown) return ''
    try {
      return DOMPurify.sanitize(marked.parse(markdown))
    } catch {
      return ''
    }
  })()

  const errorMessage = data?.errorMessage || null
  const isAvailable = status === summaryDataReducer.SummaryDataStatus.AVAILABLE && markdown
  const loading = triggering
  const isError = status === summaryDataReducer.SummaryDataStatus.ERROR
  const articleCount = data?.articleUrls?.length ?? 0

  const groupDescriptorsByDate = useCallback((articleDescriptors) => {
    const dateByUrl = new Map()
    for (const payloadDescriptor of results?.payloads || []) {
      const storageKey = getNewsletterScrapeKey(payloadDescriptor.date)
      const livePayload = getCachedStorageValue(storageKey) || payloadDescriptor
      for (const article of livePayload.articles || []) {
        dateByUrl.set(article.url, livePayload.date)
      }
    }

    const grouped = new Map()
    for (const descriptor of articleDescriptors) {
      const date = dateByUrl.get(descriptor.url)
      if (!date) continue
      if (!grouped.has(date)) grouped.set(date, [])
      grouped.get(date).push(descriptor.url)
    }
    return grouped
  }, [results?.payloads])

  const updateArticlesAcrossDates = useCallback(async (urlsByDate, updater) => {
    for (const [date, urls] of urlsByDate.entries()) {
      const urlSet = new Set(urls)
      const storageKey = getNewsletterScrapeKey(date)
      await setStorageValueAsync(storageKey, (current) => {
        const liveCurrent = current || getCachedStorageValue(storageKey)
        if (!liveCurrent) return liveCurrent

        let didChange = false
        const nextArticles = liveCurrent.articles.map((article) => {
          if (!urlSet.has(article.url)) return article
          didChange = true
          return updater(article)
        })
        if (!didChange) return liveCurrent
        return { ...liveCurrent, articles: nextArticles }
      })
    }
  }, [])

  const markDigestArticlesLoading = useCallback(async (urlsByDate) => {
    const previousSummaryByUrl = new Map()
    await updateArticlesAcrossDates(urlsByDate, (article) => {
      previousSummaryByUrl.set(article.url, article.summary)
      return {
        ...article,
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
    await updateArticlesAcrossDates(urlsByDate, (article) => {
      const previousSummary = previousSummaryByUrl.get(article.url)
      if (previousSummary == null) {
        const { summary, ...rest } = article
        return rest
      }
      return { ...article, summary: previousSummary }
    })
  }, [updateArticlesAcrossDates])

  const markDigestArticlesConsumed = useCallback(async (urlsByDate, shouldRemove) => {
    const markedAt = new Date().toISOString()
    await updateArticlesAcrossDates(urlsByDate, (article) => ({
      ...article,
      ...(shouldRemove
        ? reduceArticleLifecycle(article, { type: ArticleLifecycleEventType.MARK_REMOVED }).patch
        : reduceArticleLifecycle(article, {
            type: ArticleLifecycleEventType.MARK_READ,
            markedAt,
          }).patch),
    }))
  }, [updateArticlesAcrossDates])

  const writeDigest = useCallback((digestPatch) => {
    setPayloadRef.current(current => {
      if (!current) return current
      const fromStatus = summaryDataReducer.getSummaryDataStatus(current.digest)
      const toStatus = digestPatch.status
      if (fromStatus !== toStatus) {
        logTransition('digest', DIGEST_LOCK_OWNER, fromStatus, toStatus)
      }
      return { ...current, digest: { ...(current.digest || {}), ...digestPatch } }
    })
  }, [])

  const createRequestToken = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`

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
    if (!payload || payload.date !== pendingRequest.date) return

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

        writeDigest({ errorMessage: null })

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
          writeDigest({
            status: summaryDataReducer.SummaryDataStatus.AVAILABLE,
            markdown: result.digest_markdown,
            articleUrls: result.included_urls ?? articleUrls,
            generatedAt: new Date().toISOString(),
            effort: 'low',
            errorMessage: null,
          })
          clearSelection()
          expand()
          return
        }

        writeDigest({
          status: summaryDataReducer.SummaryDataStatus.ERROR,
          errorMessage: result.error,
        })
      } catch (error) {
        if (error.name === 'AbortError') {
          await restoreDigestArticlesSummary(urlsByDate, previousSummaryByUrl)
          return
        }
        await restoreDigestArticlesSummary(urlsByDate, previousSummaryByUrl)
        writeDigest({
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
  }, [pendingRequest, payload, targetDate, clearSelection, expand, markDigestArticlesLoading, restoreDigestArticlesSummary, writeDigest, groupDescriptorsByDate])

  useEffect(() => {
    if (status !== summaryDataReducer.SummaryDataStatus.LOADING) return
    writeDigest({
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
    html,
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
