import { useCallback, useMemo } from 'react'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import { useSupabaseStorage } from './useSupabaseStorage'

export function useArticleState(date, url) {
  const storageKey = date ? getNewsletterScrapeKey(date) : null
  const [payload, setPayload, , { loading, error }] = useSupabaseStorage(storageKey, null)

  const article = useMemo(() => {
    return payload?.articles?.find(a => a.url === url) || null
  }, [payload, url])

  const isRead = article?.read?.isRead ?? false
  const isRemoved = Boolean(article?.removed)
  const isTldrHidden = Boolean(article?.tldrHidden)

  const state = !article ? 0
    : article.removed ? 3
    : article.tldrHidden ? 2
    : article.read?.isRead ? 1
    : 0

  const updateArticle = useCallback((updater) => {
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
  }, [article, url, setPayload])

  const markAsRead = useCallback(() => {
    updateArticle(() => ({
      read: { isRead: true, markedAt: new Date().toISOString() }
    }))
  }, [updateArticle])

  const markAsUnread = useCallback(() => {
    updateArticle(() => ({
      read: { isRead: false, markedAt: null }
    }))
  }, [updateArticle])

  const toggleRead = useCallback(() => {
    if (isRead) markAsUnread()
    else markAsRead()
  }, [isRead, markAsRead, markAsUnread])

  const setRemoved = useCallback((removed) => {
    updateArticle(() => ({ removed: Boolean(removed) }))
  }, [updateArticle])

  const toggleRemove = useCallback(() => {
    setRemoved(!isRemoved)
  }, [isRemoved, setRemoved])

  const setTldrHidden = useCallback((hidden) => {
    updateArticle(() => ({ tldrHidden: Boolean(hidden) }))
  }, [updateArticle])

  const markTldrHidden = useCallback(() => {
    setTldrHidden(true)
  }, [setTldrHidden])

  const unmarkTldrHidden = useCallback(() => {
    setTldrHidden(false)
  }, [setTldrHidden])

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
