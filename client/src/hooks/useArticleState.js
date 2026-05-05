import { queueDailyArticlePatch } from '../lib/dailyPayloadMutations'
import { logTransition } from '../lib/stateTransitionLogger'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import {
  ArticleLifecycleEventType,
  getArticleLifecycleState,
  reduceArticleLifecycle,
} from '../reducers/articleLifecycleReducer'
import { useArticleSlice } from '../store/articleStore'

export function useArticleState(date, url) {
  const slice = useArticleSlice(date, url)

  const article = slice
  const isRead = slice?.read?.isRead ?? false
  const isRemoved = Boolean(slice?.removed)
  const lifecycleState = getArticleLifecycleState(slice)

  const updateArticle = (updater) => {
    if (!slice) return
    const storageKey = getNewsletterScrapeKey(date)
    queueDailyArticlePatch({
      date,
      url,
      buildPatch: updater,
      previousPayload: null,
      storageKey,
    }).catch((error) => {
      console.error(`Failed to update article for ${url}:`, error)
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
      markedAt: new Date().toISOString(),
    })
  }

  const markAsUnread = () => {
    dispatchLifecycleEvent({ type: ArticleLifecycleEventType.MARK_UNREAD })
  }

  const toggleRead = () => {
    dispatchLifecycleEvent({
      type: ArticleLifecycleEventType.TOGGLE_READ,
      markedAt: new Date().toISOString(),
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
    loading: false,
    error: null,
    markAsRead,
    markAsUnread,
    toggleRead,
    markAsRemoved,
    toggleRemove,
    updateArticle,
  }
}
