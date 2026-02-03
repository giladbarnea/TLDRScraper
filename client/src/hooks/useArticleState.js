import { getNewsletterScrapeKey } from '../lib/storageKeys'
import { logTransition } from '../lib/stateTransitionLogger'
import { useSupabaseStorage } from './useSupabaseStorage'

export function useArticleState(date, url) {
  const storageKey = getNewsletterScrapeKey(date)
  const [payload, setPayload, , { loading, error }] = useSupabaseStorage(storageKey, null)

  const article = payload?.articles?.find(a => a.url === url) || null

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

  const markAsRead = () => {
    logTransition('lifecycle', url, 'unread', 'read')
    updateArticle(() => ({
      read: { isRead: true, markedAt: new Date().toISOString() }
    }))
  }

  const markAsUnread = () => {
    logTransition('lifecycle', url, 'read', 'unread')
    updateArticle(() => ({
      read: { isRead: false, markedAt: null }
    }))
  }

  const toggleRead = () => {
    if (isRead) markAsUnread()
    else markAsRead()
  }

  const markAsRemoved = () => {
    const from = isRead ? 'read' : 'unread'
    logTransition('lifecycle', url, from, 'removed')
    updateArticle(() => ({ removed: true }))
  }

  const toggleRemove = () => {
    const from = isRemoved ? 'removed' : (isRead ? 'read' : 'unread')
    const to = isRemoved ? (isRead ? 'read' : 'unread') : 'removed'
    logTransition('lifecycle', url, from, to)
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
    markAsRemoved,
    toggleRemove,
    updateArticle
  }
}
