# Reconciliation: Domain B + Domain C

## Problem
Two parallel reducer implementations created a merge conflict in `useSummary.js`:

- **Domain B** (PR #529, merged to main): Summary **data** reducer (`unknown` → `loading` → `available`/`error`)
- **Domain C** (PR #530, still open): Summary **view** reducer (`collapsed` ↔ `expanded`)

Both modified overlapping sections of `useSummary.js` because they both replaced parts of the same ad-hoc state management.

## Root Cause
The conflict occurred because:

1. **Domain B** replaced manual data state updates with `summaryDataReducer`
2. **Domain C** replaced the simple `expanded` boolean with `summaryViewReducer`
3. Both branches were created around the same time (Feb 3, 2026)
4. Domain B merged to main first
5. Domain C's branch now conflicts with main

## Solution: Orthogonal Composition

The key insight: **both reducers should coexist** because they manage orthogonal concerns.

### Domain B: Data Lifecycle
**Responsibility**: What summary data we have and its loading state

**State**:
```javascript
{
  status: 'unknown' | 'loading' | 'available' | 'error',
  markdown: string,
  errorMessage: string | null,
  effort: 'low' | 'medium' | 'high',
  checkedAt: string | null
}
```

**Events**: `SUMMARY_REQUESTED`, `SUMMARY_LOAD_SUCCEEDED`, `SUMMARY_LOAD_FAILED`, `SUMMARY_ROLLBACK`

### Domain C: View State
**Responsibility**: How the summary is displayed (collapsed vs expanded)

**State**:
```javascript
{
  mode: 'collapsed' | 'expanded',
  expandedBy: 'tap' | 'summary-loaded' | null
}
```

**Events**: `OPEN_REQUESTED`, `CLOSE_REQUESTED`

## Reconciled Implementation

The reconciled `useSummary.js`:

1. **Imports both reducers**:
   - `summaryDataReducer` for data state
   - `summaryViewReducer` for view state

2. **Maintains separate dispatchers**:
   - `dispatchSummaryEvent()` for data transitions
   - `dispatchSummaryViewEvent()` for view transitions

3. **Coordinates at runtime**:
   - When summary loads successfully → dispatch `SUMMARY_LOAD_SUCCEEDED` (data) + `OPEN_REQUESTED` (view)
   - When user taps → dispatch `OPEN_REQUESTED` or `CLOSE_REQUESTED` (view only)
   - When fetching → dispatch `SUMMARY_REQUESTED` (data only)

4. **Preserves Domain B features**:
   - Request tokens to ignore stale responses
   - Rollback-on-abort behavior
   - Status-based loading state (no separate `loading` boolean)

5. **Adds Domain C features**:
   - View state with expand reason tracking
   - Event-driven view transitions
   - Separate view state from data state

## Key Design Decisions

### ✅ Kept: Separate Reducers
Both reducers remain independent and closed. Neither reads from the other's state.

### ✅ Kept: Runtime Coordination
The hook acts as the "mediator" that coordinates between domains by:
- Listening to data state changes
- Dispatching view events when appropriate
- Managing side effects (fetch, lock acquisition)

### ✅ Removed: Redundant Loading State
Domain C originally had a separate `loading` boolean. This was removed since Domain B's data reducer already tracks loading state via `status: 'loading'`.

### ✅ Unified: Logging Calls
Both domains use the same `logTransition` utility from `stateTransitionLogger`, maintaining consistent transition logging across the app.

## Behavioral Guarantees

The reconciled implementation maintains all behaviors from both domains:

1. **From Domain B**:
   - Summary data persisted to Supabase
   - Request tokens prevent out-of-order updates
   - Aborted fetches rollback to previous state
   - Only actual status transitions trigger logs

2. **From Domain C**:
   - View state tracked with expand reason
   - View transitions are event-driven
   - Only actual mode changes trigger logs
   - Zen lock still prevents multiple overlays

## Migration Path

This reconciliation provides a template for future reducer conflicts:

1. **Identify orthogonal concerns** - Do the reducers manage independent aspects?
2. **Keep both reducers closed** - No cross-domain state reads
3. **Coordinate at runtime** - Let the hook/component be the mediator
4. **Remove redundancy** - Eliminate duplicate state (like the extra `loading` boolean)
5. **Verify both behaviors** - Ensure no feature regression from either domain

## Files Modified
- `client/src/hooks/useSummary.js` - Integrated both dispatchers
- `client/src/reducers/summaryViewReducer.js` - Added (from Domain C branch)
- `client/src/reducers/summaryDataReducer.js` - Already present (from Domain B/main)

## Testing Notes
- Manual verification needed: summary fetch → auto-expand
- Check: abort during fetch → rollback to previous state
- Check: rapid tap-abort-tap → request token prevents stale updates
- Check: view transitions log only on actual mode changes
- Check: data transitions log only on actual status changes
