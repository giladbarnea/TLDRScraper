import { queueDailyArticlePatch } from '../lib/dailyPayloadMutations'
import { logTransition } from '../lib/stateTransitionLogger'
import {
  ArticleLifecycleEventType,
  getArticleLifecycleState,
  reduceArticleLifecycle,
} from '../reducers/articleLifecycleReducer'
import { parseArticleKey, useArticleSlice } from '../store/articleStore'

export function useArticleState(articleKey) {
  const slice = useArticleSlice(articleKey)
  const { url } = parseArticleKey(articleKey)

  const isRead = slice?.read?.isRead ?? false
  const isRemoved = Boolean(slice?.removed)
  const lifecycleState = getArticleLifecycleState(slice)

  const updateArticle = (updater) => {
    if (!slice) return
    queueDailyArticlePatch({
      key: articleKey,
      buildPatch: updater,
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
    article: slice,
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
