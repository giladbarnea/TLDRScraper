import { getNewsletterScrapeKey } from '../lib/storageKeys'
import { logTransition } from '../lib/stateTransitionLogger'
import {
  ArticleLifecycleEventType,
  getArticleLifecycleState,
  reduceArticleLifecycle
} from '../reducers/articleLifecycleReducer'
import { useSupabaseStorage } from './useSupabaseStorage'

export function useArticleState(date, url) {
  const storageKey = getNewsletterScrapeKey(date)
  const [payload, setPayload, , { loading, error }] = useSupabaseStorage(storageKey, null)

  const article = payload?.articles?.find(a => a.url === url) || null

  const lifecycleState = getArticleLifecycleState(article)
  const isRead = article?.read?.isRead ?? false
  const isRemoved = Boolean(article?.removed)

  const updateArticle = (updater) => {
    if (!article) return

    setPayload(current => {
      if (!current) return current

      return {
        ...current,
        articles: current.articles.map(a =>
          a.url === url ? { ...a, ...updater(a) } : a
        )
      }
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
