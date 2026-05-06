import { useCallback, useRef } from 'react'
import { createRequestToken } from '../lib/requestUtils'
import { scrapeNewsletters } from '../lib/scraper'
import { logTransition } from '../lib/stateTransitionLogger'
import { getDailyPayloadsRange } from '../lib/storageApi'
import { ingestFeedPayloads, setFeedRange, setFeedStatus } from '../store/articleStore'

function toIsoDateString(date) {
  return date.toISOString().split('T')[0]
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
  const requestTokenRef = useRef(null)

  const loadFeed = useCallback(async ({ startDate, endDate, signal }) => {
    const requestToken = createRequestToken()
    requestTokenRef.current = requestToken

    const range = `${startDate}..${endDate}`
    setFeedRange(startDate, endDate)
    setFeedStatus({ status: 'fetching', error: null })
    logTransition('feed', range, 'idle', 'fetching')

    let phaseOneRendered = false

    const cachedPayloads = await getDailyPayloadsRange(startDate, endDate, signal).catch(() => [])
    if (signal?.aborted) return
    if (requestTokenRef.current !== requestToken) return

    if (cachedPayloads.length > 0) {
      phaseOneRendered = true
      const cachedArticleCount = cachedPayloads.reduce((sum, payload) => sum + payload.articles.length, 0)
      logTransition('feed', range, 'fetching', 'cached', `${cachedPayloads.length} days, ${cachedArticleCount} articles`)
      ingestFeedPayloads(cachedPayloads)
      setFeedStatus({ status: 'cached' })
    }

    let freshResults
    try {
      freshResults = await scrapeNewsletters(startDate, endDate, signal)
    } catch (error) {
      if (signal?.aborted) return
      if (requestTokenRef.current !== requestToken) return
      logTransition('feed', range, phaseOneRendered ? 'cached' : 'fetching', 'error', error.message)
      setFeedStatus({ status: 'error', error: error.message })
      if (!phaseOneRendered) throw error
      return
    }

    if (signal?.aborted) return
    if (requestTokenRef.current !== requestToken) return

    ingestFeedPayloads(freshResults.payloads)
    const freshArticleCount = freshResults.payloads.reduce((sum, payload) => sum + payload.articles.length, 0)
    logTransition('feed', range, phaseOneRendered ? 'cached' : 'fetching', 'ready', `${freshResults.payloads.length} days, ${freshArticleCount} articles`)
    setFeedStatus({ status: 'ready', stats: freshResults.stats, error: null })
  }, [])

  return { loadFeed }
}
