export const ArticleLifecycleEventType = Object.freeze({
  READ_MARKED: 'READ_MARKED',
  READ_CLEARED: 'READ_CLEARED',
  REMOVED_MARKED: 'REMOVED_MARKED',
  REMOVED_TOGGLED: 'REMOVED_TOGGLED',
})

export function deriveArticleLifecycleState(article) {
  if (!article) return 'unread'
  if (article.removed) return 'removed'
  if (article.read?.isRead) return 'read'
  return 'unread'
}

export function reduceArticleLifecycle(article, event) {
  switch (event.type) {
    case ArticleLifecycleEventType.READ_MARKED:
      return {
        read: { isRead: true, markedAt: event.markedAt },
      }
    case ArticleLifecycleEventType.READ_CLEARED:
      return {
        read: { isRead: false, markedAt: null },
      }
    case ArticleLifecycleEventType.REMOVED_MARKED:
      return {
        removed: true,
      }
    case ArticleLifecycleEventType.REMOVED_TOGGLED:
      return {
        removed: !article.removed,
      }
    default:
      throw new Error(`Unknown article lifecycle event: ${event.type}`)
  }
}
