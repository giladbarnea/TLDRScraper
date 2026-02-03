export const ArticleLifecycleState = Object.freeze({
  UNREAD: 'unread',
  READ: 'read',
  REMOVED: 'removed',
})

export const ArticleLifecycleEventType = Object.freeze({
  MARK_READ: 'MARK_READ',
  MARK_UNREAD: 'MARK_UNREAD',
  TOGGLE_READ: 'TOGGLE_READ',
  MARK_REMOVED: 'MARK_REMOVED',
  TOGGLE_REMOVED: 'TOGGLE_REMOVED',
  RESTORE: 'RESTORE',
})

function buildReadPatch(isRead, markedAt) {
  if (isRead && !markedAt) {
    throw new Error('markedAt is required when setting read state.')
  }
  return {
    read: {
      isRead,
      markedAt: isRead ? markedAt : null,
    },
  }
}

export function getArticleLifecycleState(article) {
  if (article?.removed) return ArticleLifecycleState.REMOVED
  if (article?.read?.isRead) return ArticleLifecycleState.READ
  return ArticleLifecycleState.UNREAD
}

export function reduceArticleLifecycle(article, event) {
  const currentState = getArticleLifecycleState(article)
  const isRead = Boolean(article?.read?.isRead)
  const isRemoved = Boolean(article?.removed)

  switch (event.type) {
    case ArticleLifecycleEventType.MARK_READ:
      return {
        state: isRemoved ? ArticleLifecycleState.REMOVED : ArticleLifecycleState.READ,
        patch: buildReadPatch(true, event.markedAt),
      }
    case ArticleLifecycleEventType.MARK_UNREAD:
      return {
        state: isRemoved ? ArticleLifecycleState.REMOVED : ArticleLifecycleState.UNREAD,
        patch: buildReadPatch(false, null),
      }
    case ArticleLifecycleEventType.TOGGLE_READ:
      return isRead
        ? {
            state: isRemoved ? ArticleLifecycleState.REMOVED : ArticleLifecycleState.UNREAD,
            patch: buildReadPatch(false, null),
          }
        : {
            state: isRemoved ? ArticleLifecycleState.REMOVED : ArticleLifecycleState.READ,
            patch: buildReadPatch(true, event.markedAt),
          }
    case ArticleLifecycleEventType.MARK_REMOVED:
      return { state: ArticleLifecycleState.REMOVED, patch: { removed: true } }
    case ArticleLifecycleEventType.TOGGLE_REMOVED:
      return isRemoved
        ? {
            state: isRead ? ArticleLifecycleState.READ : ArticleLifecycleState.UNREAD,
            patch: { removed: false },
          }
        : { state: ArticleLifecycleState.REMOVED, patch: { removed: true } }
    case ArticleLifecycleEventType.RESTORE:
      return {
        state: isRead ? ArticleLifecycleState.READ : ArticleLifecycleState.UNREAD,
        patch: { removed: false },
      }
    default:
      return { state: currentState, patch: null }
  }
}
