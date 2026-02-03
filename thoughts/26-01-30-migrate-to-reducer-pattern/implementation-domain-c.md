# Implementation: Domain C (Summary view reducer)

## Status
✅ **Implemented**

## Overview
Domain C (summary view UI: `collapsed` ↔ `expanded`) now uses a closed reducer to centralize view transitions in one place while keeping the hook responsible for side effects and cross-domain coordination. The reducer owns the view mode and the reason it opened, while the hook handles lock acquisition, summary data fetches, and article persistence.

## Files Added
- `client/src/reducers/summaryViewReducer.js`
  - Exports `SummaryViewMode` enum (`COLLAPSED`, `EXPANDED`)
  - Exports `SummaryViewEventType` enum (`OPEN_REQUESTED`, `CLOSE_REQUESTED`)
  - Exports `reduceSummaryView(state, event)` returning `{ state }`

## Files Modified
- `client/src/hooks/useSummary.js`
  - Replaced the ad-hoc `expanded` boolean with reducer state (`summaryViewState`)
  - Added `dispatchSummaryViewEvent` to log and apply view transitions
  - Preserved the single-owner lock and summary data flow while routing view transitions through events

## Decisions (for and against)

### ✅ Adopted: Closed reducer for view mode
**Why:** The view state is a pure input/output concern, so a small reducer keeps the logic explicit and testable without pulling in other domains. It also aligns with the existing Domain A migration style.

### ✅ Adopted: Minimal event surface (`OPEN_REQUESTED`, `CLOSE_REQUESTED`)
**Why:** These two events map directly to the existing behavior and keep the reducer closed and low-ceremony. More events would be premature until Domain B is migrated.

### ❌ Deferred: Command emission for data fetch
**Why:** The current flow already fetches summary data inside the hook, and introducing commands would add boilerplate without immediate payoff. The hook still serves as the runtime that can evolve later if Domain B adopts a reducer.

### ❌ Deferred: Cross-domain mediator events (e.g., `SUMMARY_DATA_AVAILABLE`)
**Why:** The only auto-open path today is a direct consequence of a user action that triggered the fetch. The hook already has that context, so adding mediator events now would increase complexity without improving behavior.

### ✅ Retained: Single-owner lock in the hook
**Why:** The lock is inherently global and side-effectful, so keeping it out of the reducer preserves the closed reducer constraint while preventing multiple overlays.

## Behavioral Notes
- A successful summary fetch still auto-expands the view if the lock can be acquired.
- User taps open/close the view through events; view transitions are logged only on real mode changes.
- The reducer is intentionally scoped to view mode and does not read or mutate summary data or lifecycle state.
