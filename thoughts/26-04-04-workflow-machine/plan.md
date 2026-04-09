---
last_updated: 2026-04-09 09:12
---
# Plan: Reading workflow machine

## Overview

Introduce a small, explicit workflow machine for the **reading surface only**: summary surface vs digest surface, and the rules for opening, closing, and denying them.

This is intentionally **not** a new global state system and **not** a replacement for the existing domain machines. It is a narrow coordination layer whose job is to make the cross-machine protocol declarative and obvious.

## Current State Analysis

Today, the reading workflow is split across multiple owners:

- `client/src/hooks/useSummary.js`
  - owns summary data fetching
  - owns summary overlay open/close state (`expanded`)
  - owns zen-lock state indirectly via module globals (`zenLockOwner`, `acquireZenLock`, `releaseZenLock`)
  - emits toast with an `onOpen` callback bound to its own local `expand()`
- `client/src/hooks/useDigest.js`
  - owns digest generation
  - owns digest overlay open/close state (`expanded`)
  - imports and shares zen-lock functions from `useSummary.js`
  - performs digest-close lifecycle effects (mark read / mark removed)
- `client/src/App.jsx`
  - decides which dock actions are available
  - routes single/multi-selection actions
  - uses `publishArticleAction()` for summary fetch/open
- `client/src/components/ArticleCard.jsx`
  - decides whether a click opens or fetches summary
  - subscribes to `articleActionBus`
  - renders `ZenModeOverlay`
  - performs summary close/remove side effects
- `client/src/lib/articleActionBus.js`
  - acts as command transport from app-level actions to card-owned summary hooks

The result is that the core workflow rule set — “which surface is active, whether another one may open, who gets to transition next” — has no single explicit owner.

## Desired End State

There is one explicit abstraction boundary:

### Workflow machine owns
- which reading surface is active:
  - none
  - summary for URL X
  - digest
- whether an open request is allowed
- the no-preemption rule between summary and digest
- the mapping from user intent to workflow action:
  - card tap
  - toast click
  - selection dock open/digest actions
  - overlay close actions

### Existing domain machines/hooks continue to own
- article lifecycle semantics (`read`, `removed`)
- summary fetch lifecycle (`unknown/loading/available/error/rollback`)
- digest fetch/generation lifecycle
- gesture mechanics
- storage/persistence
- selection/expand state

### One-line boundary

**The workflow machine decides _which surface is active and whether a transition is allowed_; the existing machines decide _what the state means and how it persists/fetches/renders_.**

## Key Discoveries

- `useSummary.js` currently mixes **domain state** and **workflow/view state** in one hook.
- `useDigest.js` currently mixes **digest data orchestration** and **surface ownership** in one hook.
- `zenLockOwner` is currently a module-global protocol hidden inside `useSummary.js`, but it really governs behavior across `useSummary`, `useDigest`, `ArticleCard`, `DigestOverlay`, and toast clicks.
- `articleActionBus.js` is serving two different jobs today:
  1. transport for summary fetch commands
  2. transport for summary open commands
- only (1) is truly unavoidable in the current architecture; (2) exists because surface ownership is not centralized.
- summary success toast is currently emitted from `useSummary.js`, but the toast’s click behavior is a **workflow concern**, not a **summary-data concern**.

## What We're NOT Doing

- Not introducing Zustand / Redux / Jotai / XState.
- Not rewriting `InteractionContext`.
- Not changing article lifecycle semantics.
- Not changing `summaryDataReducer` semantics.
- Not changing digest generation/storage semantics.
- Not rewriting gesture hooks.
- Not touching feed-loading architecture in this effort.
- Not creating a giant superset machine for all client state.

## Implementation Approach

Use the **smallest explicit abstraction** that buys a real clarity gain:

1. Add a dedicated reading workflow reducer/context.
2. Move **surface ownership** there.
3. Remove **surface ownership** from `useSummary` and `useDigest`.
4. Keep the existing domain hooks as the source of truth for data/fetch/persistence.
5. Keep command transport minimal:
   - summary **open** becomes workflow-owned
   - summary **fetch** may continue to use a small transport path until/unless a later refactor replaces it cleanly

This is the lean, declarative version of the idea:
- explicit state and transitions
- minimal new machinery
- no broad migration of existing domain logic

---

## Phase 1: Introduce explicit reading workflow ownership

### Overview

Create the workflow boundary first, with as little behavioral change as possible.

### Changes Required

#### 1. Add a dedicated workflow reducer and context
**Files**:
- `client/src/reducers/readingWorkflowReducer.js` (new)
- `client/src/contexts/ReadingWorkflowContext.jsx` (new)

**Changes**:
- Introduce a reducer whose state is deliberately small and explicit.
- The reducer should own only the currently active reading surface.
- Preserve current behavior: **no preemption**. If one surface is active, opening the other is denied.

```js
// symbols / concepts
ReadingWorkflowState = {
  activeSurface: null | { type: 'summary', url: string } | { type: 'digest' }
}

ReadingWorkflowEventType = {
  REQUEST_SUMMARY_OPEN,
  REQUEST_DIGEST_OPEN,
  CLOSE_SUMMARY,
  CLOSE_DIGEST,
}
```

**Behavior contract**:
- `REQUEST_SUMMARY_OPEN(url)`
  - succeeds only if no surface is active
- `REQUEST_DIGEST_OPEN`
  - succeeds only if no surface is active
- `CLOSE_SUMMARY(url)`
  - only closes if summary(url) is active
- `CLOSE_DIGEST`
  - only closes if digest is active

This reducer is **not** responsible for fetch statuses, lifecycle patches, or storage.

#### 2. Provide declarative workflow API to the UI
**Files**:
- `client/src/contexts/ReadingWorkflowContext.jsx`
- `client/src/App.jsx`

**Changes**:
- Expose a small API from context, e.g.:
  - `requestSummaryOpen(url)`
  - `requestDigestOpen()`
  - `closeSummary(url)`
  - `closeDigest()`
  - `isSummaryActive(url)`
  - `isDigestActive()`
- Mount the provider in `App.jsx`/`AppContent` at the level where both `ArticleCard`s and `DigestOverlay` can consume it.

The provider should remain dumb: it owns declarative workflow state, not domain data.

#### 3. Move surface rendering decisions to workflow state
**Files**:
- `client/src/components/ArticleCard.jsx`
- `client/src/App.jsx`
- `client/src/components/DigestOverlay.jsx`

**Changes**:
- `ArticleCard` should render `ZenModeOverlay` when:
  - summary HTML is available
  - workflow says this article’s summary surface is active
- `DigestOverlay` should render when workflow says digest is active.
- The workflow context becomes the single explicit owner of “which reading surface is open”.

#### 4. Remove zen-lock ownership from hooks
**Files**:
- `client/src/hooks/useSummary.js`
- `client/src/hooks/useDigest.js`

**Changes**:
- Delete `zenLockOwner`, `acquireZenLock`, `releaseZenLock` from `useSummary.js`.
- Remove all zen-lock imports/usages from `useDigest.js`.
- Remove `expanded`, `expand`, `collapse`, `toggle` behavior from `useSummary.js`.
- Remove `expanded`, `expand`, `collapse` behavior from `useDigest.js`.

After this phase:
- `useSummary` is a summary-data hook.
- `useDigest` is a digest-data hook.
- workflow state owns only surface activation.

#### 5. Keep summary fetch transport lean for now
**Files**:
- `client/src/lib/articleActionBus.js`
- `client/src/components/ArticleCard.jsx`
- `client/src/App.jsx`

**Changes**:
- Keep `fetch-summary` transport if needed for app-level “summarize each” and “summarize single” actions.
- Remove `open-summary` transport, because opening is now workflow-owned.

This is an intentional compromise in favor of low implementation cost.

### Success Criteria

#### Automated Verification
- [ ] `cd client && npm run build`
- [ ] No references remain to `zenLockOwner`, `acquireZenLock`, or `releaseZenLock`
- [ ] No references remain to `summary.expand`, `summary.collapse`, `summary.toggle`, `digest.expand`, or `digest.collapse`

#### Manual Verification
- [ ] Only one reading surface can be open at a time
- [ ] Opening a summary while digest is open is denied
- [ ] Opening digest while a summary is open is denied
- [ ] Closing a summary removes only the active summary surface
- [ ] Closing digest removes only the digest surface
- [ ] No visual regression in either overlay

**Implementation Note**: Stop here after Phase 1 and verify that the surface-ownership boundary is clear in code before doing any cleanup of remaining workflow leaks.

---

## Phase 2: Route intent and side-effect boundaries through the workflow machine

### Overview

Now that surface ownership is explicit, move the remaining cross-machine intent routing so that the workflow machine becomes the obvious place to modify behavior across summary/digest surfaces.

### Changes Required

#### 1. Move card tap and dock open behavior to workflow actions
**Files**:
- `client/src/components/ArticleCard.jsx`
- `client/src/App.jsx`
- `client/src/components/SelectionActionDock.jsx`

**Changes**:
- `ArticleCard.handleCardClick()` should stop deciding open-vs-local-toggle.
- Replace `summary.toggle()` with explicit logic:
  - if summary data is available → `requestSummaryOpen(article.url)`
  - else → fetch summary via the existing fetch transport/path
- In `App.jsx`, single-select “Open” should call workflow `requestSummaryOpen(url)` instead of `publishArticleAction(..., 'open-summary')`.
- Multi-select digest action should explicitly:
  - trigger digest generation via the digest hook
  - request digest surface open only when the digest data is available

The goal is that **entry points express intent declaratively** and the workflow machine owns the open/close decisions.

#### 2. Move summary-success toast emission out of `useSummary`
**Files**:
- `client/src/hooks/useSummary.js`
- `client/src/components/ArticleCard.jsx`
- `client/src/lib/toastBus.js`

**Changes**:
- Remove `emitToast()` from `useSummary.js`.
- In `ArticleCard`, observe the summary status transition to `available` and emit the toast there (or in a tiny wrapper hook colocated with `ArticleCard`).
- Make toast `onOpen` dispatch `requestSummaryOpen(article.url)`.

Reason: the toast’s click behavior is a workflow concern. It should no longer be created inside the summary-data hook.

#### 3. Keep close/remove side effects in domain owners, but make them visibly separate from workflow state
**Files**:
- `client/src/components/ArticleCard.jsx`
- `client/src/App.jsx`
- `client/src/hooks/useDigest.js`

**Changes**:
- Summary overlay close path:
  - domain side effect stays local: mark article read/remove as today
  - workflow side effect is separate: clear active summary surface
- Digest overlay close path:
  - domain side effect stays with digest/article lifecycle logic
  - workflow side effect is separate: clear active digest surface

This preserves the intended boundary:
- workflow decides active surface transitions
- domain hooks decide lifecycle/data effects

#### 4. Reduce or delete leftover workflow leakage
**Files**:
- `client/src/lib/articleActionBus.js`
- `client/src/hooks/useSummary.js`
- `client/src/hooks/useDigest.js`
- `client/ALL_STATES.md`

**Changes**:
- If `articleActionBus` still only exists for summary fetch transport, document that explicitly.
- If a small direct replacement is obvious by the end of the refactor, remove the bus entirely.
- Update `client/ALL_STATES.md` to add the new workflow machine and revise the ownership map.

### Success Criteria

#### Automated Verification
- [ ] `cd client && npm run build`
- [ ] No references remain to `publishArticleAction(..., 'open-summary')`
- [ ] `useSummary.js` no longer imports `emitToast`
- [ ] `client/ALL_STATES.md` reflects the new workflow/domain boundary

#### Manual Verification
- [ ] Card tap with available summary opens via workflow state
- [ ] Card tap with unknown/error summary fetches but does not auto-open
- [ ] Toast click opens summary only when no other surface is active
- [ ] Closing summary still marks article read by default
- [ ] Check action in summary overlay still marks article removed
- [ ] Closing digest still marks digest articles read
- [ ] Check action in digest overlay still marks digest articles removed
- [ ] Selection-dock behavior still works for summarize single / summarize each / digest

---

## Testing Strategy

### Unit Tests
- Reducer tests for `readingWorkflowReducer`:
  - summary opens from idle
  - digest opens from idle
  - digest open request denied while summary active
  - summary open request denied while digest active
  - close events only affect the matching active surface

### Integration Tests
- Workflow state drives `ZenModeOverlay` visibility through `ArticleCard`
- Workflow state drives `DigestOverlay` visibility through `App.jsx`
- Summary success toast opens the correct summary surface
- Selection dock no longer uses the bus for open-summary

### Manual Testing Steps
1. Tap an article with no summary.
   - Verify summary fetch starts.
   - Verify no overlay opens immediately.
   - Verify success toast appears.
2. Click the toast.
   - Verify the corresponding article summary opens.
3. While a summary is open, trigger digest from selected articles.
   - Verify digest does not open.
4. Close the summary.
   - Verify article is marked read.
5. Trigger digest.
   - Verify digest opens.
6. While digest is open, try to open a summary.
   - Verify it is denied.
7. Close digest normally.
   - Verify included articles are marked read.
8. Re-open digest and use the remove/complete path.
   - Verify included articles are marked removed.

## References

- Discussion: `thoughts/26-04-04-workflow-machine/discussion-raw.md`
- Current state map: `client/ALL_STATES.md`
- Current summary hook: `client/src/hooks/useSummary.js`
- Current digest hook: `client/src/hooks/useDigest.js`
- Current app orchestration: `client/src/App.jsx`
- Current article workflow entry point: `client/src/components/ArticleCard.jsx`
- Current transport path: `client/src/lib/articleActionBus.js`
