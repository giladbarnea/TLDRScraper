import { useCallback, useState } from 'react'
import { mergePreservingLocalState } from '../lib/feedMerge'
import { scrapeNewsletters } from '../lib/scraper'
import { logTransition } from '../lib/stateTransitionLogger'
import { getDailyPayloadsRange } from '../lib/storageApi'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import { mergeIntoCache } from './useSupabaseStorage'

const SESSION_CACHE_TTL_MS = 10 * 60 * 1000

function toIsoDateString(date) {
  return date.toISOString().split('T')[0]
}

function getSessionCacheKey(startDate, endDate) {
  return `scrapeResults:${startDate}:${endDate}`
}

function readSessionCachedResults(startDate, endDate) {
  const cacheKey = getSessionCacheKey(startDate, endDate)
  const cachedValue = sessionStorage.getItem(cacheKey)
  if (!cachedValue) return null

  try {
    const { timestamp, data } = JSON.parse(cachedValue)
    if (Date.now() - timestamp >= SESSION_CACHE_TTL_MS) {
      sessionStorage.removeItem(cacheKey)
      return null
    }

    return data
  } catch {
    sessionStorage.removeItem(cacheKey)
    return null
  }
}

function writeSessionCachedResults(startDate, endDate, results) {
  const cacheKey = getSessionCacheKey(startDate, endDate)

  try {
    sessionStorage.setItem(cacheKey, JSON.stringify({
      timestamp: Date.now(),
      data: results
    }))
  } catch {}
}

function mergeFreshPayloadsIntoRenderedCache(cachedPayloads, freshResults, setResults) {
  const cachedDates = new Set(cachedPayloads.map((payload) => payload.date))
  const cachedUrlsByDate = new Map(
    cachedPayloads.map((payload) => [payload.date, new Set(payload.articles.map((article) => article.url))])
  )

  let newArticleCount = 0

  for (const freshPayload of freshResults.payloads) {
    if (!cachedDates.has(freshPayload.date)) continue

    const cachedUrls = cachedUrlsByDate.get(freshPayload.date)
    newArticleCount += freshPayload.articles.filter((article) => !cachedUrls.has(article.url)).length

    mergeIntoCache(
      getNewsletterScrapeKey(freshPayload.date),
      (localPayload) => mergePreservingLocalState(freshPayload, localPayload)
    )
  }

  const newDayPayloads = freshResults.payloads.filter((payload) => !cachedDates.has(payload.date))

  if (newDayPayloads.length > 0) {
    setResults((previousResults) => ({
      ...freshResults,
      payloads: [...(previousResults?.payloads || []), ...newDayPayloads]
    }))
  }

  return { newArticleCount, newDayCount: newDayPayloads.length }
}

export function getDefaultFeedDateRange() {
  const today = new Date()
  const twoDaysAgo = new Date(today)
  twoDaysAgo.setDate(today.getDate() - 2)

  return {
    startDate: toIsoDateString(twoDaysAgo),
    endDate: toIsoDateString(today)
  }
}

export function useFeedLoader() {
  const [results, setResults] = useState(null)

  const loadFeed = useCallback(async ({ startDate, endDate, signal, useSessionCache = false }) => {
    const range = `${startDate}..${endDate}`

    if (useSessionCache) {
      const sessionCachedResults = readSessionCachedResults(startDate, endDate)
      if (sessionCachedResults) {
        logTransition('feed', range, 'idle', 'ready', 'sessionStorage')
        setResults(sessionCachedResults)
        return sessionCachedResults
      }
    }

    let phaseOneRendered = false

    logTransition('feed', range, 'idle', 'fetching')

    const cachedPayloads = await getDailyPayloadsRange(startDate, endDate, signal).catch(() => [])
    if (signal?.aborted) return null

    if (cachedPayloads.length > 0) {
      phaseOneRendered = true
      const cachedArticleCount = cachedPayloads.reduce((sum, payload) => sum + payload.articles.length, 0)
      logTransition('feed', range, 'fetching', 'cached', `${cachedPayloads.length} days, ${cachedArticleCount} articles`)
      setResults({ payloads: cachedPayloads, stats: null })
    }

    const freshResults = await scrapeNewsletters(startDate, endDate, signal)
    if (signal?.aborted) return null

    if (phaseOneRendered) {
      const { newArticleCount, newDayCount } = mergeFreshPayloadsIntoRenderedCache(cachedPayloads, freshResults, setResults)
      logTransition('feed', range, 'cached', 'merged', `${newArticleCount} new articles, ${newDayCount} new days`)
    } else {
      const freshArticleCount = freshResults.payloads.reduce((sum, payload) => sum + payload.articles.length, 0)
      logTransition('feed', range, 'fetching', 'ready', `${freshResults.payloads.length} days, ${freshArticleCount} articles`)
      setResults(freshResults)
    }

    writeSessionCachedResults(startDate, endDate, freshResults)
    return freshResults
  }, [])

  return { results, setResults, loadFeed }
}
