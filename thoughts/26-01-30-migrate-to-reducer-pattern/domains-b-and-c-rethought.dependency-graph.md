---
last_updated: 2026-02-05 10:25, 03bb4c7
---
# Dependency Graph: Domain B + C Simplification (Remove Domain C reducer)

This document maps the concrete dependency tree and “area of effect” for the proposal in `thoughts/26-01-30-migrate-to-reducer-pattern/domains-b-and-c-rethought.md`: delete `client/src/reducers/summaryViewReducer.js` and simplify Domain C (summary view) inside `client/src/hooks/useSummary.js` to a plain `useState(boolean)`.

## Proposed Change Set (Code)

**Delete**
- `client/src/reducers/summaryViewReducer.js`

**Modify**
- `client/src/hooks/useSummary.js`

No other production code files currently import `summaryViewReducer.js` or call `useSummary()`.

## Area Of Effect (High-Level)

**Runtime**
- React client only (`client/src/**`)
- Summary viewing behavior inside `ArticleCard` + `ZenModeOverlay` (open/close conditions, zen lock ownership)

**Persisted storage**
- No schema changes. Domain B summary data remains persisted under `article.summary` (or `article[type]`).

**Docs/Notes (non-runtime, but will become stale if not updated)**
- `ARCHITECTURE.md` and `client/CLIENT_ARCHITECTURE.md` describe Domain C as a reducer.

---

## File-Level Dependency Mapping (Upstream + Downstream)

### 1) `client/src/reducers/summaryViewReducer.js` (to be deleted)

**Exports**
- `SummaryViewMode`
- `SummaryViewEventType`
- `reduceSummaryView(state, event)`

**Upstream callers/importers (code)**
- `client/src/hooks/useSummary.js` imports all three exports. (Only code importer.)

**Downstream callees/imports**
- None (pure, standalone module).

**Codebase usage search**
- Only `client/src/hooks/useSummary.js` imports it; the rest are documentation references. (`rg summaryViewReducer`)

**Risk**
- Low, because the reducer is not part of the public API; it is an internal implementation detail of `useSummary`.
- The actual risk is entirely mediated by how `useSummary` is refactored.

---

### 2) `client/src/hooks/useSummary.js` (to be modified)

**Export**
- `useSummary(date, url, type = 'summary')`

**Upstream callers/importers (code)**
- `client/src/components/ArticleCard.jsx` imports and calls `useSummary(article.issueDate, article.url)`. (`ArticleCard.jsx:240`)

**Downstream callees/imports (code)**
- `client/src/hooks/useArticleState.js`
  - symbols: `useArticleState()`, `updateArticle()`, `isRead`, `markAsRead`
- `client/src/lib/stateTransitionLogger.js`
  - symbols: `logTransition()`, `logTransitionSuccess()`
- `client/src/reducers/summaryDataReducer.js` (Domain B)
  - symbols: `getSummaryDataStatus()`, `reduceSummaryData()`, `SummaryDataStatus`, `SummaryDataEventType`
- `client/src/reducers/summaryViewReducer.js` (Domain C; target for removal)
  - symbols: `SummaryViewMode`, `SummaryViewEventType`, `reduceSummaryView`
- Third-party libs:
  - `marked`, `marked-katex-extension`, `dompurify`
- Platform:
  - `window.fetch('/api/summarize-url')`
  - `AbortController`

**Internal coupling points that must remain correct after refactor**
- **Zen lock**: `acquireZenLock(url)` / `releaseZenLock(url)` guards `expanded` ownership.
- **Abort/rollback**: request token + `AbortController` logic must remain unchanged to preserve Domain B correctness.
- **Read marking**: `collapse(markAsReadOnClose = true)` uses `markAsRead()` unless explicitly disabled.

**Risk**
- Medium. There is only one upstream caller, but it relies on multiple returned fields and functions.

---

## “Complete list” — Imports From `summaryViewReducer.js`

### Code imports (runtime)
- `client/src/hooks/useSummary.js` (imports `SummaryViewEventType`, `SummaryViewMode`, `reduceSummaryView`). (`useSummary.js:7`)

### Non-code references (docs/notes; not runtime)
- `ARCHITECTURE.md`
- `client/CLIENT_ARCHITECTURE.md`
- `thoughts/26-01-30-migrate-to-reducer-pattern/reconciliation-domains-b-and-c.md`
- `thoughts/26-01-30-migrate-to-reducer-pattern/domains-b-and-c-rethought.md`

These won’t break the app, but they will become misleading if Domain C stops being a reducer.

---

## “Complete list” — Files That Use The `useSummary` Hook

### Code usage (runtime)
- `client/src/components/ArticleCard.jsx` calls `useSummary(article.issueDate, article.url)`. (`ArticleCard.jsx:240`)

### Non-code references (docs/notes; not runtime)
- `ARCHITECTURE.md` (call graph / dependency graph mentions)
- `client/CLIENT_ARCHITECTURE.md`
- `thoughts/26-01-30-migrate-to-reducer-pattern/*.md` (design/implementation notes)
- `experimental/biomejs/rules/use-exhaustive-dependencies/match-1-useSummary-36.md` (also contains an outdated note about the default `type` value; see risks)

---

## All Places Where `useSummary()` Return Value Is Destructured / Used

Only `client/src/components/ArticleCard.jsx` consumes it today.

### Destructuring
- `const { isAvailable } = summary` (`ArticleCard.jsx:241`)

### Property reads
- `summary.expanded`:
  - gating swipe completion behavior (`ArticleCard.jsx:246`)
  - layout margin + styling (`ArticleCard.jsx:301`, `ArticleCard.jsx:343`)
  - data attribute (`ArticleCard.jsx:331`)
  - overlay render condition (`ArticleCard.jsx:367`)
- `summary.status`:
  - data attribute (`ArticleCard.jsx:330`)
  - error branch condition (`ArticleCard.jsx:363`)
- `summary.loading`:
  - passed to `ArticleMeta` (`ArticleCard.jsx:357`)
- `summary.errorMessage`:
  - passed to `SummaryError` (`ArticleCard.jsx:364`)
- `summary.html`:
  - overlay render condition (`ArticleCard.jsx:367`)
  - passed into `ZenModeOverlay` (`ArticleCard.jsx:370`)

### Method calls
- `summary.toggle()` (`ArticleCard.jsx:288`)
- `summary.collapse()`:
  - on swipe complete (`ArticleCard.jsx:246`)
  - overlay close (`ArticleCard.jsx:374`)
  - overlay “mark removed” flow:
    - `summary.collapse(false)` then `markAsRemoved()` (`ArticleCard.jsx:376-377`)

No other file destructures or calls anything returned from `useSummary`.

---

## Potential Breaking Changes / Overlooked Dependencies

### 1) `useSummary` public API must remain stable
**What must not change**
- Returned keys used by `ArticleCard`: `expanded`, `toggle`, `collapse`, `loading`, `status`, `errorMessage`, `html`, `isAvailable`.
- `collapse(markAsReadOnClose = true)` signature/behavior (used with `false`).

**Risk level**: Medium

### 2) `expanded` semantics must preserve zen lock gating
Current behavior:
- `expanded` only becomes true after `acquireZenLock(url)` succeeds.
- `collapse()` always `releaseZenLock(url)` before collapsing.
- unmount cleanup releases lock and aborts in-flight request.

If refactoring to `useState(expanded)`, ensure:
- you do not set `expanded=true` without acquiring the lock
- you always release the lock when collapsing

**Risk level**: Medium

### 3) View transition logging will change shape (minor)
Current behavior:
- view transitions are logged only when `summaryViewState.mode` changes, via `dispatchSummaryViewEvent`.
- The log currently does **not** include the “reason” (`tap` vs `summary-loaded`) even though `expandedBy` stores it.

If refactoring to plain `useState`, you need to decide:
- preserve logging at the same granularity (collapsed↔expanded), or
- enhance it to include reason in the log extra string (as proposed in the design doc)

**Risk level**: Low (debug-only)

### 4) Docs and “architecture truth” will diverge
`ARCHITECTURE.md` and `client/CLIENT_ARCHITECTURE.md` currently present Domain C as a reducer. Removing the reducer without updating docs will create confusion for future work.

**Risk level**: Low (no runtime effect, but high “future maintenance” cost)

### 5) `experimental/biomejs/...match-1-useSummary-36.md` already disagrees with current signature
This file states the default `type` is `'tldr'`, but `useSummary` currently defaults to `'summary'`. This is already stale; it may get further out-of-date after refactors.

**Risk level**: None (experimental / non-runtime), but it can mislead future refactors.

---

## Risk Assessment Summary (Per Dependency)

- `client/src/components/ArticleCard.jsx` (caller): **Medium** — depends on multiple returned fields and methods; breakage is immediate and visible.
- `client/src/hooks/useSummary.js` (change locus): **Medium/High** — subtle behavioral requirements (abort rollback + zen lock gating).
- `client/src/reducers/summaryViewReducer.js` (delete target): **Low** — single importer, pure module.
- `client/src/reducers/summaryDataReducer.js` (Domain B): **Low** — should remain untouched; ensure refactor doesn’t disturb event sequencing.
- `client/src/hooks/useArticleState.js`: **Low** — only used for `markAsRead` and `updateArticle`; unchanged unless the refactor alters call ordering.
- `client/src/lib/stateTransitionLogger.js`: **Low** — logging only; but keep log calls consistent to avoid noisy logs.
- `ARCHITECTURE.md`, `client/CLIENT_ARCHITECTURE.md` (docs): **Low runtime / Medium maintenance** — update recommended to keep the mental model accurate.

---

## Suggested Verification Checklist (After Implementing The Simplification)

- Summary not available → tap “Summary”:
  - status `unknown` → `loading` → `available`
  - auto-expands only if zen lock is acquired
- Tap to collapse/expand when available:
  - toggles `expanded` state, respects zen lock
- Swipe-to-remove while expanded:
  - calls `summary.collapse()` before removal (current behavior)
- Abort during fetch:
  - rolls back to previous summary data
  - does not leave `status='loading'` stuck

