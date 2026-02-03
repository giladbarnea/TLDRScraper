import { getNewsletterScrapeKey } from '../lib/storageKeys'
import {
  ArticleLifecycleEventType,
  ArticleLifecycleState,
  deriveArticleLifecycleState,
  reduceArticleLifecycle
} from '../reducers/articleLifecycleReducer'
import { useSupabaseStorage } from './useSupabaseStorage'

export function useArticleState(date, url) {
  const storageKey = getNewsletterScrapeKey(date)
  const [payload, setPayload, , { loading, error }] = useSupabaseStorage(storageKey, null)

  const article = payload?.articles?.find(a => a.url === url) || null

  const lifecycleState = deriveArticleLifecycleState(article)
  const isRead = lifecycleState === ArticleLifecycleState.READ
  const isRemoved = lifecycleState === ArticleLifecycleState.REMOVED

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

  const updateLifecycle = (event) => {
    updateArticle(current => reduceArticleLifecycle(current, event).patch)
  }

  const markAsRead = () => {
    updateLifecycle({
      type: ArticleLifecycleEventType.READ_MARKED,
      markedAt: new Date().toISOString(),
    })
  }

  const markAsUnread = () => {
    updateLifecycle({ type: ArticleLifecycleEventType.READ_CLEARED })
  }

  const toggleRead = () => {
    if (isRead) markAsUnread()
    else markAsRead()
  }

  const markAsRemoved = () => {
    updateLifecycle({ type: ArticleLifecycleEventType.REMOVED_MARKED })
  }

  const toggleRemove = () => {
    updateLifecycle({
      type: isRemoved
        ? ArticleLifecycleEventType.REMOVED_RESTORED
        : ArticleLifecycleEventType.REMOVED_MARKED
    })
  }

  return {
    article,
    isRead,
    isRemoved,
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
