import { getNewsletterScrapeKey } from '../lib/storageKeys'
import { useSupabaseStorage } from './useSupabaseStorage'

export function useArticleState(date, url) {
  const storageKey = getNewsletterScrapeKey(date)
  const [payload, setPayload, , { loading, error }] = useSupabaseStorage(storageKey, null)

  const article = payload?.articles?.find(a => a.url === url) || null

  const isRead = article?.read?.isRead ?? false
  const isRemoved = Boolean(article?.removed)
  console.log('[useArticleState] render', { url, isRemoved, articleRemoved: article?.removed })

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

  const markAsRead = () => {
    updateArticle(() => ({
      read: { isRead: true, markedAt: new Date().toISOString() }
    }))
  }

  const markAsUnread = () => {
    updateArticle(() => ({
      read: { isRead: false, markedAt: null }
    }))
  }

  const toggleRead = () => {
    if (isRead) markAsUnread()
    else markAsRead()
  }

  const toggleRemove = () => {
    updateArticle(() => ({ removed: !isRemoved }))
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
    toggleRemove,
    updateArticle
  }
}
