export const ArticleLifecycleState = Object.freeze({
  UNREAD: 'unread',
  READ: 'read',
  REMOVED: 'removed',
})

export const ArticleLifecycleEventType = Object.freeze({
  READ_MARKED: 'READ_MARKED',
  READ_CLEARED: 'READ_CLEARED',
  REMOVED_MARKED: 'REMOVED_MARKED',
  REMOVED_RESTORED: 'REMOVED_RESTORED',
})

export function deriveArticleLifecycleState(article) {
  if (!article) return ArticleLifecycleState.UNREAD
  if (article.removed) return ArticleLifecycleState.REMOVED
  if (article.read?.isRead) return ArticleLifecycleState.READ
  return ArticleLifecycleState.UNREAD
}

function deriveRestoredState(article) {
  return article.read?.isRead ? ArticleLifecycleState.READ : ArticleLifecycleState.UNREAD
}

export function reduceArticleLifecycle(article, event) {
  const currentState = deriveArticleLifecycleState(article)

  switch (event.type) {
    case ArticleLifecycleEventType.READ_MARKED:
      if (currentState === ArticleLifecycleState.REMOVED) {
        throw new Error('Cannot mark as read while removed.')
      }
      return {
        state: ArticleLifecycleState.READ,
        patch: { read: { isRead: true, markedAt: event.markedAt } },
      }
    case ArticleLifecycleEventType.READ_CLEARED:
      if (currentState === ArticleLifecycleState.REMOVED) {
        throw new Error('Cannot mark as unread while removed.')
      }
      return {
        state: ArticleLifecycleState.UNREAD,
        patch: { read: { isRead: false, markedAt: null } },
      }
    case ArticleLifecycleEventType.REMOVED_MARKED:
      return {
        state: ArticleLifecycleState.REMOVED,
        patch: { removed: true },
      }
    case ArticleLifecycleEventType.REMOVED_RESTORED:
      if (currentState !== ArticleLifecycleState.REMOVED) {
        throw new Error('Cannot restore when not removed.')
      }
      return {
        state: deriveRestoredState(article),
        patch: { removed: false },
      }
    default:
      throw new Error(`Unknown article lifecycle event: ${event.type}`)
  }
}
