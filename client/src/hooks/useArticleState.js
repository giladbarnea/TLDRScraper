import { getNewsletterScrapeKey } from '../lib/storageKeys'
import { useSupabaseStorage } from './useSupabaseStorage'

export function useArticleState(date, url) {
  const storageKey = getNewsletterScrapeKey(date)
  const [payload, setPayload, , { loading, error }] = useSupabaseStorage(storageKey, null)

  const article = payload?.articles?.find(a => a.url === url) || null

  const isRead = article?.read?.isRead ?? false
  const isRemoved = Boolean(article?.removed)
  const isTldrHidden = Boolean(article?.tldrHidden)

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

  const toggleRemove = () => {
    updateArticle(() => ({ removed: !isRemoved }))
  }

  const markTldrHidden = () => {
    updateArticle(() => ({ tldrHidden: true }))
  }

  const unmarkTldrHidden = () => {
    updateArticle(() => ({ tldrHidden: false }))
  }

  return {
    article,
    isRead,
    isRemoved,
    isTldrHidden,
    loading,
    error,
    toggleRemove,
    markTldrHidden,
    unmarkTldrHidden,
    updateArticle
  }
}
