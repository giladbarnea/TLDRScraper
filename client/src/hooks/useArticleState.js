import { logTransition } from '../lib/stateTransitionLogger'
import { getDailyPayloadWithMetadata, patchDailyArticle } from '../lib/storageApi'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import {
  ArticleLifecycleEventType,
  getArticleLifecycleState,
  reduceArticleLifecycle
} from '../reducers/articleLifecycleReducer'
import { setStorageValueInMemory, useSupabaseStorage } from './useSupabaseStorage'

function applyArticlePatchToPayload(payload, url, articlePatch) {
  if (!payload) return payload
  return {
    ...payload,
    articles: payload.articles.map((article) =>
      article.url === url ? { ...article, ...articlePatch } : article
    )
  }
}

export function useArticleState(date, url) {
  const storageKey = getNewsletterScrapeKey(date)
  const [payload, , , { loading, error }] = useSupabaseStorage(storageKey, null)

  const article = payload?.articles?.find(a => a.url === url) || null

  const lifecycleState = getArticleLifecycleState(article)
  const isRead = article?.read?.isRead ?? false
  const isRemoved = Boolean(article?.removed)

  const updateArticle = (updater) => {
    if (!article) return
    const previousPayload = payload
    const optimisticPatch = updater(article)
    if (!optimisticPatch || Object.keys(optimisticPatch).length === 0) return

    const optimisticPayload = applyArticlePatchToPayload(previousPayload, url, optimisticPatch)
    setStorageValueInMemory(storageKey, optimisticPayload)

    const persistPatch = async () => {
      let latestPayload = optimisticPayload
      let latestPatch = optimisticPatch
      let expectedUpdatedAt = latestPayload.storage_updated_at

      for (let attemptIndex = 0; attemptIndex < 2; attemptIndex += 1) {
        if (!expectedUpdatedAt) {
          const storageRow = await getDailyPayloadWithMetadata(date)
          if (!storageRow) throw new Error(`Daily payload not found for date: ${date}`)
          latestPayload = storageRow.payload
          expectedUpdatedAt = storageRow.updatedAt
          const latestArticle = latestPayload.articles.find((currentArticle) => currentArticle.url === url)
          if (!latestArticle) throw new Error(`Article not found for url: ${url}`)
          setStorageValueInMemory(storageKey, applyArticlePatchToPayload(latestPayload, url, latestPatch))
        }

        const patchResult = await patchDailyArticle(date, {
          url,
          patch: latestPatch,
          expectedUpdatedAt
        })

        if (patchResult.success) {
          setStorageValueInMemory(storageKey, patchResult.payload)
          return
        }

        if (!patchResult.conflict) {
          throw new Error('Daily article patch failed')
        }

        latestPayload = patchResult.payload
        expectedUpdatedAt = patchResult.updatedAt
        const latestArticle = latestPayload.articles.find((currentArticle) => currentArticle.url === url)
        if (!latestArticle) throw new Error(`Article not found for url: ${url}`)
        setStorageValueInMemory(storageKey, applyArticlePatchToPayload(latestPayload, url, latestPatch))
      }

      throw new Error('Daily article patch conflict retry exhausted')
    }

    persistPatch().catch((persistError) => {
      console.error(`Failed to update article for ${url}:`, persistError)
      setStorageValueInMemory(storageKey, previousPayload)
    })
  }

  const dispatchLifecycleEvent = (event) => {
    updateArticle((current) => {
      const fromState = getArticleLifecycleState(current)
      const { state: toState, patch } = reduceArticleLifecycle(current, event)
      if (fromState !== toState) {
        logTransition('lifecycle', url, fromState, toState)
      }
      return patch || {}
    })
  }

  const markAsRead = () => {
    dispatchLifecycleEvent({
      type: ArticleLifecycleEventType.MARK_READ,
      markedAt: new Date().toISOString()
    })
  }

  const markAsUnread = () => {
    dispatchLifecycleEvent({ type: ArticleLifecycleEventType.MARK_UNREAD })
  }

  const toggleRead = () => {
    dispatchLifecycleEvent({
      type: ArticleLifecycleEventType.TOGGLE_READ,
      markedAt: new Date().toISOString()
    })
  }

  const markAsRemoved = () => {
    dispatchLifecycleEvent({ type: ArticleLifecycleEventType.MARK_REMOVED })
  }

  const toggleRemove = () => {
    dispatchLifecycleEvent({ type: ArticleLifecycleEventType.TOGGLE_REMOVED })
  }

  return {
    article,
    isRead,
    isRemoved,
    lifecycleState,
    loading,
    error,
    markAsRead,
    markAsUnread,
    toggleRead,
    markAsRemoved,
    toggleRemove,
    updateArticle
  }
}
