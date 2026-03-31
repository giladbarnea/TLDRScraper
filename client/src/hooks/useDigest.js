import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { useEffect, useRef, useState } from 'react'
import { useInteraction } from '../contexts/InteractionContext'
import { logTransition } from '../lib/stateTransitionLogger'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import * as summaryDataReducer from '../reducers/summaryDataReducer'
import { acquireZenLock, releaseZenLock } from './useSummary'
import { useSupabaseStorage } from './useSupabaseStorage'

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
  const loading = triggering || status === summaryDataReducer.SummaryDataStatus.LOADING
  const isError = status === summaryDataReducer.SummaryDataStatus.ERROR
  const articleCount = data?.articleUrls?.length ?? 0

  const writeDigest = (digestPatch) => {
    setPayloadRef.current(current => {
      if (!current) return current
      const fromStatus = summaryDataReducer.getSummaryDataStatus(current.digest)
      const toStatus = digestPatch.status
      if (fromStatus !== toStatus) {
        logTransition('digest', DIGEST_LOCK_OWNER, fromStatus, toStatus)
      }
      return { ...current, digest: { ...(current.digest || {}), ...digestPatch } }
    })
  }

  const createRequestToken = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`

  const trigger = (articleDescriptors) => {
    const payloads = results?.payloads
    if (!payloads || payloads.length === 0) return
    if (!articleDescriptors || articleDescriptors.length < 2) return

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

  useEffect(() => {
    if (!pendingRequest) return
    if (targetDate !== pendingRequest.date) return
    if (!payload || payload.date !== pendingRequest.date) return

    const { articleDescriptors, requestToken } = pendingRequest
    const articleUrls = articleDescriptors.map(d => d.url)
    const controller = new AbortController()
    abortControllerRef.current = controller
    setPendingRequest(null)

    const runDigest = async () => {
      try {
        writeDigest({
          status: summaryDataReducer.SummaryDataStatus.LOADING,
          effort: 'low',
          errorMessage: null,
        })

        const response = await window.fetch('/api/digest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ articles: articleDescriptors, effort: 'low' }),
          signal: controller.signal,
        })

        const result = await response.json()

        if (requestTokenRef.current !== requestToken) return

        if (result.success) {
          const successPatch = {
            status: summaryDataReducer.SummaryDataStatus.AVAILABLE,
            markdown: result.digest_markdown,
            articleUrls: result.included_urls ?? articleUrls,
            generatedAt: new Date().toISOString(),
            effort: 'low',
            errorMessage: null,
          }
          setPayloadRef.current(current => {
            if (!current) return current
            logTransition('digest', DIGEST_LOCK_OWNER, summaryDataReducer.SummaryDataStatus.LOADING, summaryDataReducer.SummaryDataStatus.AVAILABLE)
            return { ...current, digest: { ...(current.digest || {}), ...successPatch } }
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
          return
        }
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
  }, [pendingRequest, payload, targetDate, clearSelection])

  const expand = () => {
    if (acquireZenLock(DIGEST_LOCK_OWNER)) {
      logTransition('digest-view', DIGEST_LOCK_OWNER, 'collapsed', 'expanded', 'tap')
      setExpanded(true)
    }
  }

  const collapse = () => {
    logTransition('digest-view', DIGEST_LOCK_OWNER, 'expanded', 'collapsed')
    releaseZenLock(DIGEST_LOCK_OWNER)
    setExpanded(false)
  }

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
