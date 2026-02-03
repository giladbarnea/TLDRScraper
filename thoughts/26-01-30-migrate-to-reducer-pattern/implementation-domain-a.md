# Implementation: Domain A - Article Lifecycle State Machine

## Status
✅ **Implemented** (commits: 2c21304, 3a54a61)

## Overview
Domain A (Article lifecycle: `unread` → `read` → `removed`) has been migrated to a closed reducer pattern following the guidance in `discussion.md` and the domain modeling in `articlecard-state-suggestion.md`.

## Files Added
- `client/src/reducers/articleLifecycleReducer.js`
  - Exports `ArticleLifecycleState` enum (`UNREAD`, `READ`, `REMOVED`)
  - Exports `ArticleLifecycleEventType` enum (`MARK_READ`, `MARK_UNREAD`, `TOGGLE_READ`, `MARK_REMOVED`, `TOGGLE_REMOVED`, `RESTORE`)
  - Exports `getArticleLifecycleState(article)` - derives current state from article data
  - Exports `reduceArticleLifecycle(article, event)` - pure reducer returning `{ state, patch }`

## Files Modified
- `client/src/hooks/useArticleState.js`
  - Introduced `dispatchLifecycleEvent(event)` function that:
    - Calls the reducer to compute next state and storage patch
    - Logs state transitions via `logTransition` (integration with main branch logging feature)
    - Applies the patch via existing `updateArticle` mechanism
  - Refactored all lifecycle operations (`markAsRead`, `markAsUnread`, `toggleRead`, `markAsRemoved`, `toggleRemove`) to dispatch events instead of imperatively mutating state
  - Exposed `lifecycleState` from the hook so consumers can observe high-level state without duplicating logic

## Implementation Patterns

### Closed Reducer
The reducer is **closed** per the migration playbook:
- No cross-domain reads (doesn't access other state machines)
- No side effects (pure function)
- No hidden inputs (only `article` state and `event` payload)

### Event-Driven Architecture
Components dispatch **events** (what happened) rather than calling setters (what to do):
```javascript
// Before: Imperative
markAsRead(() => ({ read: { isRead: true, markedAt: ... } }))

// After: Event-driven
dispatchLifecycleEvent({ type: ArticleLifecycleEventType.MARK_READ, markedAt: ... })
```

### Storage Contract
The reducer returns a `patch` object that describes the minimal storage update:
```javascript
{ state: 'read', patch: { read: { isRead: true, markedAt: '...' } } }
```

The patch is applied via the existing `updateArticle` mechanism, preserving the current Supabase sync layer.

## Integration with Main Branch (Rebase Resolution)

During the rebase onto main, a conflict arose because main had added transition logging via `logTransition` in the imperative handlers, while the Domain A branch had replaced those handlers with reducer-based dispatches.

**Resolution**: Integrated logging into the reducer pattern by adding transition detection in `dispatchLifecycleEvent`:
```javascript
const dispatchLifecycleEvent = (event) => {
  updateArticle((current) => {
    const fromState = getArticleLifecycleState(current)
    const { state: toState, patch } = reduceArticleLifecycle(current, event)
    if (fromState !== toState) {
      logTransition('lifecycle', url, fromState, toState)
    }
    return patch || {}
  })
}
```

**Behavioral improvement**: Unlike main's imperative logging (which logged even on no-ops like marking an already-read article as read), the new implementation only logs actual state transitions.

## Reducer Enforcement: `markedAt` Contract

The reducer enforces that `markedAt` must be provided when marking an article as read:
```javascript
function buildReadPatch(isRead, markedAt) {
  if (isRead && !markedAt) {
    throw new Error('markedAt is required when setting read state.')
  }
  // ...
}
```

All read-setting events (`MARK_READ`, `TOGGLE_READ`) provide `markedAt` in their payload.

## Testing
- Manual verification via Codex review (see rebase resolution)
- `npm ci && npm run build` passes
- No automated tests (client package has no test script configured)

## Next Steps (Other Domains)
Per `articlecard-state-suggestion.md`, the remaining domains to migrate are:
- **Domain B** - Summary data (async): `unknown` → `loading` → `available` / `error`
- **Domain C** - Summary view (UI): `collapsed` ↔ `expanded`
- **Domain D** - Gesture (UI): `idle` ↔ `dragging` ↔ `select-mode`

Domain A provides the reference implementation pattern for these migrations.
