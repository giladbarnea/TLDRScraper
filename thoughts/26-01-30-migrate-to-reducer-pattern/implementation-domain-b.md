---
last_updated: 2026-02-03 15:01, f034482
---
# Implementation: Domain B - Summary Data Reducer

## Overview
Domain B (summary data: `unknown` → `loading` → `available` / `error`) now uses a closed reducer to drive state transitions inside `useSummary`. The reducer owns the persisted summary data (`status`, `markdown`, `errorMessage`, `checkedAt`, `effort`), while the hook continues to orchestrate side effects (fetching summaries, expanding the view, and acquiring/releasing the zen lock).

## Decisions (and why)
- **Added a closed reducer (`summaryDataReducer`)** to centralize summary data transitions and remove ad-hoc patch logic. This mirrors Domain A’s lifecycle reducer and keeps the summary data domain pure and testable.
- **Stored `loading` in persisted summary data** so the UI can rely on a single source of truth for summary status. This removes the prior split between in-memory loading state and stored status.
- **Introduced lightweight request tokens in `useSummary` (not persisted)** to ignore stale responses while avoiding additional fields in Supabase. This keeps the data model clean while preventing out-of-order updates.
- **Rollback on abort** restores the prior summary data snapshot when a fetch is aborted without replacement, so cached state is not left in a perpetual loading state.

## Decisions Against (and why)
- **Did not persist request tokens in Supabase** because they are transient, add no user value, and would pollute cached data with ephemeral state.
- **Did not introduce a mediator or command runtime layer** for summary data yet. The hook already acts as the runtime, and adding a new orchestration layer would add boilerplate without immediate payoff.
- **Did not expand to Domain C/D reducers** in this iteration to keep the change surgical and focused on the requested Domain B migration.

## Files Touched
- `client/src/reducers/summaryDataReducer.js`
- `client/src/hooks/useSummary.js`
