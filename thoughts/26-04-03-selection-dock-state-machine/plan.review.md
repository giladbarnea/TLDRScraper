---
last_updated: 2026-04-04 12:10, bc67602
---
# Plan Review: Selection Dock State Machine + Summary-Aware Buttons

**Plan**: `thoughts/26-04-03-selection-dock-state-machine/plan.md`  
**Status**: Request Changes  
**Reviewed against**: current `work` branch after `6ea59f2` (`feat(client): integrate digest lifecycle with article state transitions`) and `5ffa6d3` (`feat(client): move multi-selection actions to iOS-style bottom dock`)

## Critical Issues (Must Fix)

- [ ] **State ownership**: I recommend not deriving the dock state machine from `results.payloads` in `App.jsx`.
  - *Why*: `AppContent` currently reads selection descriptors from `results?.payloads` in `client/src/App.jsx:35-55`, but those payloads stop being authoritative after mount. Live article state flows through `useSupabaseStorage` inside `CalendarDay` (`client/src/components/CalendarDay.jsx:51-63`) and then through `useArticleState` / `useSummary`. `mergeIntoCache()` also mutates the shared cache without updating `results` (`client/src/hooks/useSupabaseStorage.js:251-256`). A dock derived from `results` will drift on `read`, `removed`, and especially `summary.status`.
  - *Suggestion*: derive dock availability from live storage-backed data, not from `results`. A dock-specific hook that subscribes to the relevant daily payloads would be safer than centralizing this in `App.jsx`.

- [ ] **Secondary `useSummary()` instances will not open the real summary overlay**: I recommend rethinking the proposed `SelectionActionController`.
  - *Why*: `useSummary()` owns its own local `expanded` state (`client/src/hooks/useSummary.js:28-34,188-193`), but the actual `ZenModeOverlay` is rendered only inside `ArticleCard` when that specific hook instance has `summary.expanded === true` (`client/src/components/ArticleCard.jsx:229-230,353-366`). Calling `summary.expand()` from a controller instance will not open the existing card overlay. The same problem applies to the summary-ready toast path: `emitToast({ onOpen: expand })` binds the toast to the hook instance that fetched the summary (`client/src/hooks/useSummary.js:123-130`), and `ToastContainer` simply calls that callback (`client/src/components/ToastContainer.jsx:21-24`).
  - *Suggestion*: keep the persisted summary data shared, but introduce a separate shared “open summary by URL” mechanism if the dock must open overlays. I would avoid duplicating `useSummary()` instances as the control surface.

- [ ] **Batching through per-article hooks is riskier than the plan assumes**: I recommend not implementing batch read/remove/summarize-each as “loop over N selected `useArticleState()` / `useSummary()` instances”.
  - *Why*: `useArticleState.updateArticle()` writes the entire daily payload via `setPayload(current => ...)` (`client/src/hooks/useArticleState.js:20-33`), and `useSummary()` does the same through `updateArticle()` (`client/src/hooks/useSummary.js:58-80`). In `useSupabaseStorage`, each hook instance resolves updater functions against its own `valueRef.current` (`client/src/hooks/useSupabaseStorage.js:214-239`). If several selected articles share the same `issueDate`, N sibling hook instances can resolve against stale per-instance state and overwrite each other.
  - *Suggestion*: group selected articles by `issueDate` and perform one payload write per date, or serialize writes per date. `useDigest` already uses the safer pattern: one `setPayload()` call updates all matching articles in the active payload (`client/src/hooks/useDigest.js:60-116`).

- [ ] **The plan assumes a stronger digest coupling than the code currently has**: I recommend explicitly accounting for multi-date selection before depending on digest-induced summary states.
  - *Why*: `useDigest` binds itself to a single `targetDate` storage key (`client/src/hooks/useDigest.js:14-19,31-35,146-157`). Its side effects only traverse `current.articles` in that one payload (`client/src/hooks/useDigest.js:60-116`). So a digest over articles from multiple dates does not mark every selected article `summary.loading`, and later does not mark every selected article read/removed on collapse. This may already be a latent bug, but it becomes load-bearing for your dock plan because the plan explicitly wants summarize buttons to react to digest-driven summary transitions.
  - *Suggestion*: either constrain the new dock behavior to same-date selections, or fix cross-date digest side effects first so the dock is not built on top of an incomplete source of truth.

- [ ] **The summarize action matrix is still underspecified for `loading` and `error`**: I recommend tightening this before implementation.
  - *Why*: the plan says single-select summarize should disable while loading, but multi-select “summarize each” only skips `available`. In the actual hook, any non-available state falls through to `fetchSummary()` (`client/src/hooks/useSummary.js:168-178`), and `fetchSummary()` will abort/restart the current request for that hook instance (`client/src/hooks/useSummary.js:84-105`). For the dock, `loading` needs to be treated as inactive/no-op, and `error` likely needs to be treated as retryable.
  - *Suggestion*: define an explicit `actionableForSummarizeEach` set. I would make it `unknown` + `error`, while `loading` is skipped and `available` is complete.

## Suggestions (Optional)

- [ ] Consider keeping `SelectionActionDock.jsx` dumb and feeding it a declarative action list with stable IDs. That will make button animation, keying, and single-vs-multi transitions easier to reason about than branching ad hoc in `App.jsx`.

- [ ] Consider a stronger mobile layout plan before implementation. The current dock is a single `max-w-md` row with `min-w-20` buttons (`client/src/components/SelectionActionDock.jsx:3-15`), and the feed only budgets `pb-24` below the content (`client/src/components/Feed.jsx:3-9`). Five actions in single-select mode will be cramped on small screens unless you intentionally redesign the dock hierarchy.

- [ ] Consider extracting the “openable URL” normalization from `ArticleCard` (`client/src/components/ArticleCard.jsx:248-260`) instead of reimplementing it in the dock for `Browse`.

## Blindspot Check

- [ ] What should `Open` do if the digest overlay already owns the zen lock? Today `expand()` simply no-ops when `acquireZenLock()` fails (`client/src/hooks/useSummary.js:14-25,188-193`).

- [ ] What should happen to selection after single-item `Browse` or `Open`? The plan defines clearing after batch read/remove, but not after the single-item actions.

- [ ] How should `Summarize Each` look when the selection is mixed: some `available`, some `loading`, some `error`, some `unknown`?

- [ ] Do you want equal visual weight for all actions? With five buttons, I would expect at least one stronger primary action and one clearly destructive action, otherwise the dock will get visually noisy quickly.

## Codebase Reality Check

- `results.payloads` in `App.jsx` are not the live article-state source after initial render; `CalendarDay` and all per-article hooks read from `useSupabaseStorage`.
- `useSummary.expand()` only affects the hook instance that owns it; the rendered summary overlay still lives in `ArticleCard`.
- `useDigest` currently mutates only the most recent selected date's payload, not every selected article across dates.
