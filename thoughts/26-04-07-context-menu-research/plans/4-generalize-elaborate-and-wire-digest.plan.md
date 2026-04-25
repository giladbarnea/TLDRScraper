---
originates_from: plans/3-define-shared-overlay-menu-contract-then-wire-digest.plan.md
last_updated: 2026-04-25 17:54
---

# Generalize Elaborate Endpoint And Wire Digest As Menu Consumer Implementation Plan

## Overview

Land the deferred half of plan 3: make `DigestOverlay` a real consumer of the shared overlay-menu contract, with the same `Elaborate` action as Zen and no Digest-specific action set. To do that, `/api/elaborate` must accept a context shape that fits both summaries and digests, because Zen's current contract assumes a single `url` plus a single `summary_markdown` and Digest has neither.

This plan should land **after** `plans/3-define-shared-overlay-menu-contract-then-wire-digest.plan.md` is shipped and verified. Plan 3 establishes the menu surface contract on `BaseOverlay` and aligns Digest's mount lifecycle with Zen. Without that groundwork, this plan would re-introduce the asymmetry plan 3 just removed.

### Decision journey

The deferral in plan 3 left an explicit fork: how does Digest get the `Elaborate` action without being given a bespoke action set? Three shapes were considered:

1. **Two endpoints** — keep `/api/elaborate` for Zen, add `/api/elaborate-digest` for Digest. **Rejected**: doubles the action handlers, doubles the prompt templates, and violates the "Digest inherits Zen's actions undifferentiated" goal — actions would dispatch to different endpoints.
2. **Tagged-union request** — `/api/elaborate` accepts a `source: { kind: 'article_url' | 'digest', ... }` discriminated union. **Rejected**: more validation than the two-case shape warrants. Tagged unions earn their cost when there are three or more variants.
3. **One endpoint with optional `article_url`** (this plan) — `/api/elaborate` accepts required `selected_text` + `source_markdown`, plus optional `article_url`. When `article_url` is present, the server scrapes it and includes the article body in the LLM prompt. When absent, the LLM elaborates from `source_markdown` alone. The frontend caller decides which fields to send. This is the smallest delta that supports both consumers under one action.

A fourth option — drop the article-body scrape from Zen entirely and elaborate from the summary alone — was considered and rejected. It would simplify the API but is a quality regression for an existing feature with no measured baseline. Deferring article-body context to "when the caller has it" is the disciplined cut.

## Current State Analysis

The elaboration path is single-summary specific end to end:

- `serve.py:152-166` requires `url`, `selected_text`, and `summary_markdown` in the JSON body and forwards all three to `tldr_app.elaborate_url`.
- `tldr_app.py:70-89` forwards the three fields to `tldr_service.elaborate_url_content`.
- `tldr_service.py:439-458` validates that all three are non-empty, canonicalizes `url`, and calls `summarizer.elaborate_url`.
- `summarizer.py:310-330` builds a prompt with three sections — `<selected-text-to-elaborate-on>`, `<summary>`, `<original-article>` — and `summarizer.py:333-343` scrapes the URL to fill `<original-article>`.

The frontend has exactly one caller:

- `client/src/components/ZenModeOverlay.jsx:34-92` owns `runElaboration`, the `AbortController`, the elaboration state machine (`idle | loading | available | error`), and renders `ElaborationPreview`. The `Elaborate` action is defined inline at `:94-106`.

After plan 3 ships:

- `BaseOverlay` accepts the `overlayMenu` contract and renders `OverlayContextMenu` when present.
- `ZenModeOverlay` passes the contract via `overlayMenu` and still owns elaboration state and `ElaborationPreview` directly.
- `DigestOverlay` is mounted only while open, has no `useOverlayContextMenu` instance, and does not render the menu.
- `useDigest.js` exposes `html` but not `markdown` (`:45, :290`). The hook computes both.

The product constraint that makes Digest different from Zen:

- Zen's user is reading a *summary* of one article. The "deeper truth" the LLM can pull on is the article body (scraped from `url`). The summary is the framing the user sees.
- Digest's user is reading a *synthesized digest* of multiple articles. There is no single "deeper truth" to scrape, and there are no callers willing to scrape N articles for an inline elaboration. The digest itself is the framing the user sees, and elaborating from that framing alone is the well-formed shape.

## Key Discoveries

- The shared concept across both consumers is "the markdown the user is reading from." Calling that `summary_markdown` is a misnomer once Digest is a caller. Renaming to `source_markdown` keeps the field name honest.
- `url` becoming optional warrants a more specific name: `article_url` distinguishes "the deeper article behind the source" from the source itself.
- Elaboration domain (`useElaboration` shape: state + run + close + abort) is duplicated by Zen today. Once Digest needs the same shape, the right cut is a shared hook in `client/src/hooks/`, not a second hoist into `BaseOverlay`. `BaseOverlay` already accepts one contract (overlay menu); a second contract starts the path to a god-component.
- `ElaborationPreview` is presentational — it takes `status`, `selectedText`, `markdown`, `errorMessage`, `onClose`. It is already overlay-agnostic. Each wrapper rendering it is small wiring, not duplication that needs collapsing.
- The current elaborate prompt has three sections (`selected-text`, `summary`, `original-article`). Removing the third section when no article is available is a minimal branch in `_build_elaborate_prompt`. The prompt's instructional preamble ("Draw from the original article to provide more depth...") is the load-bearing copy that needs an alternate phrasing for the no-article path.

## Desired End State

After this plan is implemented:

- `/api/elaborate` accepts `selected_text` (required), `source_markdown` (required), and `article_url` (optional). The legacy field names `url` and `summary_markdown` are gone end-to-end. There is no backwards compatibility shim; this is an internal API and the frontend ships in lockstep.
- `tldr_service.elaborate_content` (renamed from `elaborate_url_content`) and `summarizer.elaborate` (renamed from `elaborate_url`) take `source_markdown` plus an optional `article_url`. When present, the server scrapes the article and adds it to the LLM prompt; when absent, the prompt has two sections instead of three.
- `_build_elaborate_prompt` branches once on whether the article body is provided. The instructional preamble adapts to "elaborate from the source" vs. "elaborate from the source and the underlying article."
- A new shared hook `useElaboration({ sourceMarkdown, articleUrl })` lives in `client/src/hooks/useElaboration.js` and owns the run/close/abort lifecycle and elaboration state. It is the only place in the client that posts to `/api/elaborate`.
- `ZenModeOverlay` calls `useElaboration({ sourceMarkdown: summaryMarkdown, articleUrl: url })`, defines the `Elaborate` action against the hook's `runElaboration`, passes the `overlayMenu` contract to `BaseOverlay`, and renders `<ElaborationPreview>` against the hook's state.
- `DigestOverlay` calls `useOverlayContextMenu(true)`, calls `useElaboration({ sourceMarkdown: digestMarkdown })` with no `articleUrl`, defines an `Elaborate` action with the same key/label/icon as Zen, passes the `overlayMenu` contract to `BaseOverlay`, and renders `<ElaborationPreview>` against the hook's state.
- `useDigest.js` exposes `markdown` alongside `html` so `DigestOverlay` can pass it through.
- `App.jsx` passes `markdown` from `digest` into `DigestOverlay`.
- Docs describe Digest as a real menu consumer with an Elaborate action that operates on the digest markdown without scraping any article.

## What We Are Not Doing

- No Floating UI or BaseUI migration.
- No focus-stack or nested-layer ownership rewrite.
- No streaming response support for elaboration.
- No backend rate limiting, quota, or per-user gating.
- No prompt caching of any layer.
- No multi-action expansion of the menu beyond Elaborate. If/when more actions are added, that is its own scoping decision.
- No reuse of digest-cached elaborations across renders. Each `Elaborate` triggers a fresh fetch, same as Zen today.
- No `BaseOverlay` involvement in elaboration. The shell's contract surface stays the single `overlayMenu` prop introduced in plan 3.
- No backwards compatibility on the API. Old field names go away entirely; the lone client caller migrates in the same change.
- No prompt redesign beyond the conditional inclusion of `<original-article>` and the matching preamble adjustment.
- No change to `OverlayContextMenu`, `useOverlayContextMenu`, or the menu surface contract from plan 3.

## Implementation Approach

Generalize the backend first; then extract the shared elaboration hook; then migrate Zen onto the hook; then wire Digest as the second consumer; then update docs.

The five-phase split keeps each step independently verifiable. Backend changes can be exercised via `curl` before any frontend work begins. The hook extraction is a behavior-preserving Zen refactor. Digest wiring is the only step that introduces a new user-facing capability.

The layering rule this plan preserves:

```text
wrapper owns menu state, action definitions, and per-action domain hooks
shared hook owns one action's lifecycle (runElaboration + state + abort)
BaseOverlay owns the menu surface contract only
```

`useElaboration` is a wrapper-side capability shared between consumers. It does not move into `BaseOverlay` because elaboration is one possible action among many, not a universal overlay concern.

## Phase 1: Generalize The Elaborate Endpoint

### Overview

Make the backend accept the new shape end-to-end. No frontend change yet.

### Changes Required

#### 1. Update the HTTP endpoint

**File**: `serve.py`

The endpoint should require `selected_text` and `source_markdown` and accept optional `article_url`. The docstring should describe the new shape.

#### 2. Update the application layer

**File**: `tldr_app.py`

Rename `elaborate_url` to `elaborate` and update its arg list to `(selected_text, source_markdown, *, article_url=None, model)`. The response shape should include `canonical_url` only when `article_url` was provided; otherwise omit that field rather than returning an empty string.

#### 3. Update the service layer

**File**: `tldr_service.py`

Rename `elaborate_url_content` to `elaborate_content`. Validate `selected_text` and `source_markdown` as non-empty. Validate `article_url` only when present. Canonicalize `article_url` only when present. Pass `source_markdown` and the optional scraped article body to `summarizer.elaborate`.

#### 4. Update the summarizer layer

**Files**: `summarizer.py`

Rename `elaborate_url` to `elaborate`. Its signature becomes `(selected_text, source_markdown, *, article_url=None, model)`. When `article_url` is provided, scrape it and pass the article body; otherwise pass `None`. `_build_elaborate_prompt` should accept `article_markdown: str | None` and branch:

- When `article_markdown` is present, keep the current three-section prompt.
- When absent, emit a two-section prompt (`<selected-text-to-elaborate-on>` + `<source>`) with a preamble that says the elaboration should draw from the source itself rather than from a separate underlying article.

Update the doctest to cover both branches.

### Decision rationale

Renaming `summary_markdown` to `source_markdown` and `url` to `article_url` is the disciplined choice. Keeping `summary_markdown` would force every Digest reader to mentally remap "summary" to "digest" forever; keeping `url` as required would either lie or accept dummy values from Digest callers. Renaming costs one frontend touchpoint and pays back permanently in clarity.

Branching `_build_elaborate_prompt` once is preferred over building two prompt functions. The branch is one conditional and one alternate preamble line; two functions would duplicate the surrounding instructional copy.

### Verification

- `curl -X POST http://localhost:5001/api/elaborate -H 'Content-Type: application/json' -d '{"selected_text":"...","source_markdown":"...","article_url":"https://..."}'` returns `success: true` with `elaboration_markdown` and `canonical_url`.
- `curl -X POST http://localhost:5001/api/elaborate -H 'Content-Type: application/json' -d '{"selected_text":"...","source_markdown":"..."}'` returns `success: true` with `elaboration_markdown` and no `canonical_url`.
- Sending the legacy field names returns 400 (`KeyError`-driven) — the rename is total.

## Phase 2: Extract The Shared Elaboration Hook

### Overview

Move Zen's elaboration lifecycle into a shared hook without changing visible Zen behavior.

### Changes Required

#### 1. Create `useElaboration`

**File**: `client/src/hooks/useElaboration.js` (new)

The hook accepts `{ sourceMarkdown, articleUrl }` (the latter optional) and returns:

- `elaboration` — the state object (`status`, `selectedText`, `markdown`, `errorMessage`)
- `runElaboration(selectedText)` — fires the request, owns the `AbortController`, advances state through `loading → available | error`
- `closeElaboration()` — aborts the in-flight request, resets to idle

The hook should:

- Build the request body with `selected_text`, `source_markdown`, and `article_url` only when `articleUrl` is provided.
- Trim selected text inside `runElaboration` so callers do not have to (matching the current Zen logic).
- Abort any in-flight request on unmount.

#### 2. Keep `ElaborationPreview` unchanged

**File**: `client/src/components/ElaborationPreview.jsx`

The component is already presentational and takes the right props. No changes here.

### Decision rationale

The hook returns the lifecycle primitives rather than composing the preview itself because consumers may want to render the preview at different points in their tree (for example, alongside other Zen-only or Digest-only siblings). Returning the data and giving the wrapper the render decision is the more flexible cut for two callers, and it keeps the hook a pure logic primitive.

The hook lives at `client/src/hooks/useElaboration.js` rather than next to `OverlayContextMenu` because elaboration is not a menu concern. The menu happens to invoke it; the hook itself is independent of the menu's existence.

### Verification

After this phase Zen behavior is unchanged because Zen still imports the hook and renders the same JSX; the change is purely internal. Confirm by re-running the manual Zen verification steps from plan 3.

## Phase 3: Migrate Zen Onto The Shared Hook

### Overview

Replace Zen's inline elaboration code with the shared hook.

### Changes Required

#### 1. Use `useElaboration` from Zen

**File**: `client/src/components/ZenModeOverlay.jsx`

Replace the inline `IDLE_ELABORATION`, `useState(IDLE_ELABORATION)`, `abortControllerRef`, `closeElaboration`, and `runElaboration` with one call:

```text
const { elaboration, runElaboration, closeElaboration } =
  useElaboration({ sourceMarkdown: summaryMarkdown, articleUrl: url })
```

The `Elaborate` action body becomes a thin trampoline that calls `runElaboration(selectedText)`. The `<ElaborationPreview>` JSX reads from `elaboration` and calls `closeElaboration` on close.

The `useEffect` that aborted on unmount goes away because the hook owns abort-on-unmount.

#### 2. Confirm Zen behavior is identical

The visible Zen behavior should remain unchanged: right-click opens the menu, mobile selection opens the menu, `Elaborate` opens the preview with the captured selected text, escape and backdrop close the preview.

### Decision rationale

This phase is intentionally a behavior-preserving refactor. Holding it as its own phase makes regressions easy to spot — if Zen breaks here, the issue is in the hook extraction, not in the Digest wiring that follows.

## Phase 4: Wire Digest As Menu Consumer

### Overview

Make `DigestOverlay` consume the menu surface contract from plan 3 and the elaboration hook from phase 2, with an `Elaborate` action identical to Zen's.

### Changes Required

#### 1. Expose the digest markdown from `useDigest`

**File**: `client/src/hooks/useDigest.js`

Add `markdown` to the hook's return object alongside `html`. The value already exists as a local variable.

#### 2. Pass markdown into `DigestOverlay`

**File**: `client/src/App.jsx`

Forward `markdown={digest.markdown}` in the conditional `<DigestOverlay />` render.

#### 3. Compose the menu and elaboration hooks in `DigestOverlay`

**File**: `client/src/components/DigestOverlay.jsx`

Add a `markdown` prop. Inside the component:

- Call `useOverlayContextMenu(true)`.
- Call `useElaboration({ sourceMarkdown: markdown })` — no `articleUrl`.
- Define an `actions` array with a single `Elaborate` action whose `key`, `label`, `icon`, and trim-then-run behavior match Zen's exactly. The only difference is the closure capturing Digest's `runElaboration`.
- Build the `overlayMenu` contract object from the menu hook state and the action list.
- Pass the contract into `BaseOverlay`.
- Render `<ElaborationPreview>` against the elaboration hook's state.

The `Elaborate` action definition should be identical text and identical icon component — copy-paste, not abstraction. With only two callers, an "actions factory" abstraction is premature; the duplication is a few lines and signals the action's portability.

### Decision rationale

The `Elaborate` action being copy-pasted between Zen and Digest is intentional. The rule "actions are wrapper-owned" from plan 3 is preserved. If a third consumer ever appears, *then* extracting an `elaborateAction(runElaboration)` builder is the right move. Doing it now is an abstraction without a second example.

`DigestOverlay` does not gain Zen's `articleUrl` plumbing because the digest has no single article. Passing `articleUrl: undefined` is exactly what the optional-field design expects.

### Verification

- Right-click inside the digest prose opens the menu.
- The menu shows `Elaborate` with the same icon and label as Zen.
- Selecting `Elaborate` opens `ElaborationPreview` with the digest's selected text and a backend response that did not scrape any article (verified via server logs showing no Firecrawl call for this request).
- Closing the digest while elaboration is in-flight aborts the request cleanly (verified via the AbortError log in `useElaboration`).
- Mobile text selection inside the digest opens the menu after finger lift, same as Zen.
- The `ElaborationPreview` Escape/backdrop dismissal works the same in Digest as in Zen.

## Phase 5: Update Documentation And Research Notes

### Overview

Reflect the new endpoint shape and the second menu consumer in the docs.

### Changes Required

#### 1. Update the API documentation in source comments and docstrings

**Files**: `serve.py`, `tldr_app.py`, `tldr_service.py`, `summarizer.py`

Each layer's docstring should describe the new arg names, the optional `article_url` semantics, and the two prompt branches.

#### 2. Update the client docs

**Files**: `client/ARCHITECTURE.md`, `client/STATE_MACHINES.md`

Document that:

- `useElaboration` is a shared hook; both `ZenModeOverlay` and `DigestOverlay` instantiate it.
- The `Elaborate` action is consumer-defined but identical in shape across both overlays.
- `DigestOverlay` is now a menu consumer; the menu surface contract is fully shared.
- Digest elaboration does not scrape any article; the digest markdown is the only LLM context beyond the selection.

#### 3. Update the research trail

**Files**: `thoughts/26-04-07-context-menu-research/0-b-feature-map.md`, `thoughts/26-04-07-context-menu-research/implementation/iteration-3.md` (or a new iteration file)

Update the feature map so it shows two consumers, an optional `article_url`, and the prompt branch. Add an implementation log recording:

- the rename from `summary_markdown` / `url` to `source_markdown` / `article_url`
- the prompt branch for no-article elaboration
- the `useElaboration` extraction
- the Digest menu wiring
- explicit non-goals reaffirmed: no streaming, no caching, no multi-action expansion

Do not manually edit YAML timestamp fields.

## Acceptance Criteria

### Automated Verification

- [ ] `cd client && npm run build`
- [ ] `cd client && CI=1 npm run lint`
- [ ] `uv run pytest -q` passes (covers the renamed service/summarizer functions and the doctest in `_build_elaborate_prompt`).
- [ ] `rg -n "summary_markdown" .` returns no matches outside historical thought files.
- [ ] `rg -n "elaborate_url\\b" .` returns no matches in production code.
- [ ] `rg -n "useElaboration" client/src` shows the hook used in both `ZenModeOverlay.jsx` and `DigestOverlay.jsx`.
- [ ] `rg -n "useOverlayContextMenu\\(" client/src/components` shows both `ZenModeOverlay.jsx` and `DigestOverlay.jsx`.
- [ ] `rg -n "/api/elaborate" client/src` shows exactly one caller — `client/src/hooks/useElaboration.js`.

Only fix build, lint, or test failures introduced by this work.

### Manual Verification

#### Backend shapes

1. `curl` with `selected_text`, `source_markdown`, and `article_url` returns `success: true` with `elaboration_markdown` and `canonical_url`. Server logs show one Firecrawl call.
2. `curl` with only `selected_text` and `source_markdown` returns `success: true` with `elaboration_markdown` and no `canonical_url`. Server logs show no Firecrawl call.
3. `curl` with the old field names (`summary_markdown`, `url`) returns 400.

#### Zen regression

1. Open a summary overlay, right-click in the prose, choose `Elaborate`.
2. Confirm the preview opens with the selected text and the elaboration draws on article-level depth (qualitative — should reference details that are in the article but compressed in the summary).
3. Confirm Escape closes preview only on first press, overlay only on second press.
4. Repeat on mobile selection.

#### Digest as a menu consumer

1. Trigger a digest from the selection dock.
2. Right-click in the digest prose; confirm the custom menu opens with `Elaborate`.
3. Choose `Elaborate`; confirm the preview opens with the selected text and a coherent elaboration that references the digest's framing.
4. Confirm server logs show no Firecrawl call for this request.
5. Close the digest while a slow elaboration is still loading; confirm the request aborts cleanly (the abort log fires; no stale response updates state).
6. On mobile, select text inside the digest; confirm the menu opens after finger lift.

#### Cross-consumer check

1. Open a Zen summary, run `Elaborate`, close it. Open a digest, run `Elaborate`, close it. Confirm neither overlay's elaboration state leaks into the other.

## Risk Notes

- The rename is total. There is no transitional period where both old and new field names work. The frontend and backend must ship together.
- The prompt branch for the no-article case is the load-bearing copy change. A bad alternate preamble can produce flat, generic elaborations from digests. After implementation, run a small qualitative check on three real digest selections before declaring this phase done.
- `useElaboration` aborts on unmount. Digest unmounts when collapsed (per plan 3), so closing a digest mid-elaboration triggers the same abort path Zen uses. If plan 3's mount-lifecycle change has a regression, this plan will inherit it.
- Copy-pasting the `Elaborate` action between Zen and Digest is deliberate. Do not extract a builder yet; the second example is not enough signal for the right abstraction shape.
- Digest's `markdown` exposure is a small public-surface widening on `useDigest`. The hook already computes the value; this just stops hiding it. No state-machine consequences.
- The action set staying minimal (`Elaborate` only) is a scoping choice, not a final answer. Future plans may add Digest-specific actions, Zen-specific actions, or shared actions; this plan does not commit to any of them.
- The later focus-stack / BaseUI work should still be straightforward after this change because the new hook does not touch overlay-stack arbitration.

## References

- `thoughts/26-04-07-context-menu-research/impl-review/0-g-review-1.md`
- `thoughts/26-04-07-context-menu-research/plans/3-define-shared-overlay-menu-contract-then-wire-digest.plan.md`
- `thoughts/26-04-07-context-menu-research/0-b-feature-map.md`
- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`
- `client/src/App.jsx`
- `client/src/components/BaseOverlay.jsx`
- `client/src/components/ZenModeOverlay.jsx`
- `client/src/components/DigestOverlay.jsx`
- `client/src/components/OverlayContextMenu.jsx`
- `client/src/components/ElaborationPreview.jsx`
- `client/src/hooks/useDigest.js`
- `client/src/hooks/useOverlayContextMenu.js`
- `serve.py`
- `tldr_app.py`
- `tldr_service.py`
- `summarizer.py`
