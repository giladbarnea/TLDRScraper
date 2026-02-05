# Domains B and C: Rethought Design

## Current State Assessment

After implementing the reconciliation of Domain B (summary data) and Domain C (summary view), the architecture feels more complex than necessary:

- **Domain B (data reducer)**: Manages `unknown` → `loading` → `available`/`error` with request tokens, rollback, and persistence. **This is good complexity** - it handles genuinely complex async state.

- **Domain C (view reducer)**: Manages `collapsed` ↔ `expanded` with optional `expandedBy` metadata. **This is unnecessary complexity** - it's essentially a boolean with extra ceremony.

The reconciled implementation requires:
- 2 separate reducers
- 2 separate dispatchers in `useSummary`
- Coordination logic between domains
- ~40 lines in `summaryViewReducer.js` for what could be one line of `useState`

## The Core Principle

**Use reducers for complex state, `useState` for simple state.**

**When to use a reducer:**
- State has complex transitions with invariants to maintain
- Multiple events affect the same state in non-trivial ways
- State needs persistence or cross-component sharing
- You need strong guarantees about state consistency

**When to use `useState`:**
- It's a boolean, number, or simple value
- Transitions are straightforward (toggle, set)
- State is local to a component/hook
- No complex coordination needed

Domain B meets the first criteria. Domain C does not.

## Proposed Simplification

### Remove
- `client/src/reducers/summaryViewReducer.js` (entire file - 45 lines)
- `dispatchSummaryViewEvent` function
- `summaryViewState` useState
- All `SummaryViewEventType.OPEN_REQUESTED`/`CLOSE_REQUESTED` event dispatching
- Coordination logic between reducers

### Keep
- Domain B reducer (it handles genuinely complex state)
- Request token logic
- Rollback on abort
- All actual functionality

### Replace
```javascript
// Before:
const [summaryViewState, setSummaryViewState] = useState({
  mode: SummaryViewMode.COLLAPSED,
  expandedBy: null,
})

const dispatchSummaryViewEvent = (event) => {
  setSummaryViewState((current) => {
    const { state: next } = reduceSummaryView(current, event)
    if (current.mode !== next.mode) {
      logTransition('summary-view', url, current.mode, next.mode)
    }
    return next
  })
}

// When data loads:
dispatchSummaryViewEvent({
  type: SummaryViewEventType.OPEN_REQUESTED,
  reason: 'summary-loaded',
})

// After:
const [expanded, setExpanded] = useState(false)

// When data loads:
if (acquireZenLock(url)) {
  logTransition('summary-view', url, 'collapsed', 'expanded', 'summary-loaded')
  setExpanded(true)
}
```

## Implementation Changes

### File: `client/src/hooks/useSummary.js`

**Remove imports:**
```javascript
import {
  SummaryViewEventType,
  SummaryViewMode,
  reduceSummaryView,
} from '../reducers/summaryViewReducer'
```

**Simplify state:**
```javascript
// Before:
const [summaryViewState, setSummaryViewState] = useState({
  mode: SummaryViewMode.COLLAPSED,
  expandedBy: null,
})
const isExpanded = summaryViewState.mode === SummaryViewMode.EXPANDED

// After:
const [expanded, setExpanded] = useState(false)
```

**Simplify toggle/expand/collapse:**
```javascript
const toggle = (summaryEffort) => {
  if (isAvailable) {
    if (expanded) {
      collapse()
    } else if (acquireZenLock(url)) {
      logTransition('summary-view', url, 'collapsed', 'expanded', 'tap')
      setExpanded(true)
    }
  } else {
    fetchSummary(summaryEffort)
  }
}

const collapse = (markAsReadOnClose = true) => {
  logTransition('summary-view', url, 'expanded', 'collapsed')
  releaseZenLock(url)
  setExpanded(false)
  if (markAsReadOnClose && !isRead) markAsRead()
}

const expand = () => {
  if (acquireZenLock(url)) {
    logTransition('summary-view', url, 'collapsed', 'expanded', 'tap')
    setExpanded(true)
  }
}
```

**Simplify auto-expand on load:**
```javascript
if (result.success) {
  dispatchSummaryEvent({
    type: summaryDataReducer.SummaryDataEventType.SUMMARY_LOAD_SUCCEEDED,
    markdown: result.summary_markdown,
    effort: summaryEffort,
    checkedAt: new Date().toISOString(),
  })
  requestTokenRef.current = null
  previousSummaryDataRef.current = null

  if (acquireZenLock(url)) {
    logTransition('summary-view', url, 'collapsed', 'expanded', 'summary-loaded')
    setExpanded(true)
  }
}
```

**Return value:**
```javascript
return {
  data,
  status,
  markdown,
  html,
  errorMessage,
  loading: isLoading,
  expanded,  // Simple boolean instead of isExpanded derived from summaryViewState
  effort,
  isAvailable,
  isError,
  fetch: fetchSummary,
  toggle,
  collapse,
  expand
}
```

### File to delete: `client/src/reducers/summaryViewReducer.js`

This entire file can be removed.

## Benefits

1. **~40 fewer lines of code** (summaryViewReducer.js)
2. **Simpler mental model**: "One reducer for complex data, simple state for simple UI"
3. **Easier to understand**: No second dispatcher, no coordination ceremony
4. **Same functionality**: Nothing is lost - we still track transitions, still log, still coordinate
5. **Consistent with React idioms**: Reducers for complex state, useState for simple state
6. **Better alignment with Domain A**: Article lifecycle justifies a reducer (complex transitions), view expansion does not

## What About `expandedBy` Tracking?

The current implementation tracks `expandedBy: 'tap' | 'summary-loaded'`. This is nice-to-have debugging metadata, but:
- It's never read by any other code
- It only exists for potential future debugging
- We already log the transition with the reason

If we ever need it, we can add it back as:
```javascript
const expand = (reason = 'tap') => {
  logTransition('summary-view', url, 'collapsed', 'expanded', reason)
  setExpanded(true)
}
```

The logging preserves the information without needing to store it in state.

## Migration Strategy

1. Read dependency graph to understand all callers/callees
2. Update `useSummary.js` to remove Domain C reducer
3. Delete `summaryViewReducer.js`
4. Update any components that directly import from `summaryViewReducer` (likely none)
5. Update architecture documentation to reflect simplified design
6. Test: summary fetch, expand/collapse, zen lock coordination

## Expected Impact

**Files modified:**
- `client/src/hooks/useSummary.js` (~20 lines simpler)

**Files deleted:**
- `client/src/reducers/summaryViewReducer.js`

**Files potentially affected:**
- Components using `useSummary` hook (check return value usage)
- Architecture documentation

**No breaking changes expected:**
- The hook's public API remains identical
- `expanded` is still a boolean, just named `expanded` instead of computed from `isExpanded`
- All functionality preserved

## Comparison Table

| Aspect | Domain C Reducer (Current) | Simple useState (Proposed) |
|--------|---------------------------|---------------------------|
| Lines of code | ~85 (reducer + hook logic) | ~45 (hook logic only) |
| Files | 2 (reducer + hook) | 1 (hook only) |
| Complexity | High (dual reducers + coordination) | Low (single reducer + simple state) |
| Testability | Same | Same |
| Debugging | Slightly easier (expandedBy) | Same (logs capture reason) |
| Mental model | "Two coordinated state machines" | "Complex state + simple state" |
| Consistency | Inconsistent (boolean doesn't need reducer) | Consistent (useState for booleans) |

## Conclusion

Domain C was over-engineered. The reducer pattern is excellent for Domain B's complex async data lifecycle, but overkill for a simple boolean view state. By simplifying to `useState(expanded)`, we reduce cognitive load, remove ~40 lines of code, and maintain all functionality while adhering to React best practices.
