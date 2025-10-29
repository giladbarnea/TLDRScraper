/**
 * useArticleState - Manages individual article state (read/removed)
 * Provides reactive access to article properties and state mutations
 */
import { computed } from 'vue'
import { useLocalStorage } from './useLocalStorage'

export function useArticleState(date, url) {
  const storageKey = `newsletters:scrapes:${date}`
  const { data: payload } = useLocalStorage(storageKey, null)

  // Find the article in the payload
  const article = computed(() => {
    if (!payload.value?.articles) return null
    return payload.value.articles.find(a => a.url === url)
  })

  // Computed state properties
  const isRead = computed(() =>
    article.value?.read?.isRead ?? false
  )

  const isRemoved = computed(() =>
    Boolean(article.value?.removed)
  )

  const state = computed(() => {
    if (!article.value) return 0
    if (article.value.removed) return 2
    if (article.value.read?.isRead) return 1
    return 0  // unread
  })

  // State mutation methods
  function markAsRead() {
    if (!article.value) return
    article.value.read = {
      isRead: true,
      markedAt: new Date().toISOString()
    }
  }

  function markAsUnread() {
    if (!article.value) return
    article.value.read = {
      isRead: false,
      markedAt: null
    }
  }

  function toggleRead() {
    if (isRead.value) {
      markAsUnread()
    } else {
      markAsRead()
    }
  }

  function setRemoved(removed) {
    if (!article.value) return
    article.value.removed = Boolean(removed)
  }

  function toggleRemove() {
    setRemoved(!isRemoved.value)
  }

  // Update article with custom updater function
  function updateArticle(updater) {
    if (!article.value) return null
    const updated = updater(article.value)
    Object.assign(article.value, updated)
    return article.value
  }

  return {
    article,
    isRead,
    isRemoved,
    state,
    markAsRead,
    markAsUnread,
    toggleRead,
    setRemoved,
    toggleRemove,
    updateArticle
  }
}
