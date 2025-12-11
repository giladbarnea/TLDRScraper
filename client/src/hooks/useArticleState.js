import { getNewsletterScrapeKey } from '../lib/storageKeys'
import { useSupabaseStorage } from './useSupabaseStorage'

export function useArticleState(date, url) {
  const storageKey = getNewsletterScrapeKey(date)
  const [payload, setPayload, , { loading, error }] = useSupabaseStorage(storageKey, null)

  const article = payload?.articles?.find(a => a.url === url) || null

  const isRead = article?.read?.isRead ?? false
  const isRemoved = Boolean(article?.removed)
  const isTldrHidden = Boolean(article?.tldrHidden)

  const state = !article ? 0
    : article.removed ? 3
    : article.tldrHidden ? 2
    : article.read?.isRead ? 1
    : 0

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

  const setRemoved = (removed) => {
    updateArticle(() => ({ removed: Boolean(removed) }))
  }

  const toggleRemove = () => {
    setRemoved(!isRemoved)
  }

  const setTldrHidden = (hidden) => {
    updateArticle(() => ({ tldrHidden: Boolean(hidden) }))
  }

  const markTldrHidden = () => {
    setTldrHidden(true)
  }

  const unmarkTldrHidden = () => {
    setTldrHidden(false)
  }

  return {
    article,
    isRead,
    isRemoved,
    isTldrHidden,
    state,
    loading,
    error,
    markAsRead,
    markAsUnread,
    toggleRead,
    setRemoved,
    toggleRemove,
    setTldrHidden,
    markTldrHidden,
    unmarkTldrHidden,
    updateArticle
  }
}
