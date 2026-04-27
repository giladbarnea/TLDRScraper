---
originates_from: plans/3-define-shared-overlay-menu-contract-then-wire-digest.plan.md
last_updated: 2026-04-27 21:21, b387f55
implemented_by: implementation/3-b-generalize-elaborate-and-wire-digest.md
---

# Generalize Elaborate Endpoint And Wire Digest As Menu Consumer Implementation Plan

## Overview

Land the deferred half of plan 3: make `DigestOverlay` a real consumer of the shared overlay-menu contract, with the same `Elaborate` action as Zen and no Digest-specific action set. To do that, `/api/elaborate` must accept a context shape that fits both summaries and digests, because Zen's current contract assumes a single `url` plus a single `summary_markdown` and Digest has multiple source URLs and a synthesized digest markdown.

This plan should land **after** `plans/3-define-shared-overlay-menu-contract-then-wire-digest.plan.md` is shipped and verified. Plan 3 establishes the menu surface contract on `BaseOverlay` and aligns Digest's mount lifecycle with Zen. Without that groundwork, this plan would re-introduce the asymmetry plan 3 just removed.

### Decision journey

The deferral in plan 3 left an explicit fork: how does Digest get the `Elaborate` action without being given a bespoke action set? Four shapes were considered:

1. **Two endpoints** — keep `/api/elaborate` for Zen, add `/api/elaborate-digest` for Digest. **Rejected**: doubles the action handlers, doubles the prompt templates, and violates the "Digest inherits Zen's actions undifferentiated" goal — actions would dispatch to different endpoints.
2. **Tagged-union request** — `/api/elaborate` accepts a `source: { kind: 'article_url' | 'digest', ... }` discriminated union. **Rejected**: more validation than the two-case shape warrants. Tagged unions earn their cost when there are three or more variants.
3. **One endpoint with optional `article_url`** — `/api/elaborate` accepts required `selected_text` + `source_markdown`, plus optional `article_url`. The backend branches on presence: scrape if given, otherwise prompt without article context. **Rejected**: an optional field forces a branch in `_build_elaborate_prompt`, two preamble copies, and an asymmetric quality story (Digest elaborations would have less context than Zen's). The "is the menu calling from a digest?" knowledge leaks into the prompt design.
4. **One endpoint with required `article_urls` list (this plan)** — `/api/elaborate` accepts required `selected_text`, required `source_markdown`, and required non-empty `article_urls: list[str]`. Zen sends a one-element list (the article URL); Digest sends the digest's source URL list. The backend always scrapes all URLs in parallel and always builds the same three-section prompt. No branching. The shape is uniform across consumers; only the list length differs.

A fifth option — drop the article-body scrape entirely and elaborate from the source markdown alone — was considered and rejected. It would simplify the API but is a quality regression for an existing feature with no measured baseline. Always providing article-level context is the disciplined cut.

The list-shaped option won because it removes the largest source of complexity from option 3: the optional-field branch and its accompanying alternate prompt copy. The cost is that Digest elaborations now scrape N articles in parallel (more network, more LLM tokens), but the codebase already has a `ThreadPoolExecutor`-based parallel scrape helper at `tldr_service.py:310-343` for exactly this shape, so reuse is direct.

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
- `useDigest.js` exposes `html` and `articleCount` but not `markdown` or `articleUrls` (`:51, :287-300`). Both values are computed internally on `data`.

The product fit between the two consumers under the new shape:

- Zen reads a *summary* of one article. Its source URL list is `[url]`. The LLM sees: selected text + summary markdown + the one scraped article body.
- Digest reads a *synthesized digest* of multiple articles. Its source URL list is `data.articleUrls` from `useDigest` (already populated when the digest is available — see `useDigest.js:218`). The LLM sees: selected text + digest markdown + all scraped article bodies.

The codebase already supports the parallel-scrape shape:

- `tldr_service.py:310-343` defines `_fetch_articles_content_parallel`, which uses `ThreadPoolExecutor(max_workers=5)` to call `summarizer.url_to_markdown` for a list of articles. Reuse this pattern directly. A thinner sibling helper that takes raw URLs (no title/category metadata) may be appropriate for the elaborate path.

## Key Discoveries

- The shared concept across both consumers is "the markdown the user is reading from" plus "the underlying source articles." Calling those `summary_markdown` and `url` is a misnomer once Digest is a caller. Renaming to `source_markdown` and `article_urls` keeps the field names honest.
- A required non-empty list is the cleanest shape: Zen sends `[url]`, Digest sends `data.articleUrls`. The backend never branches on "is there an article?"
- Elaboration domain (`useElaboration` shape: state + run + close + abort) is duplicated by Zen today. Once Digest needs the same shape, the right cut is a shared hook in `client/src/hooks/`, not a second hoist into `BaseOverlay`. `BaseOverlay` already accepts one contract (overlay menu); a second contract starts the path to a god-component.
- `ElaborationPreview` is presentational — it takes `status`, `selectedText`, `markdown`, `errorMessage`, `onClose`. It is already overlay-agnostic. Each wrapper rendering it is small wiring, not duplication that needs collapsing.
- The current elaborate prompt has a section literally named `<original-article>` (singular). Renaming to `<source-articles>` (plural) lets the same section hold 1..N concatenated article bodies, matching the new request shape with no other prompt structural change.
- The existing `_fetch_articles_content_parallel` helper already implements parallel scrape with `as_completed` semantics. The elaborate path should reuse this pattern, not invent a parallel mechanism.

## Desired End State

After this plan is implemented:

- `/api/elaborate` accepts `selected_text` (required, non-empty string), `source_markdown` (required, non-empty string), and `article_urls` (required, non-empty list of strings). The legacy field names `url` and `summary_markdown` are gone end-to-end. There is no backwards compatibility shim; this is an internal API and the frontend ships in lockstep.
- `tldr_service.elaborate_content` (renamed from `elaborate_url_content`) and `summarizer.elaborate` (renamed from `elaborate_url`) take `source_markdown` and `article_urls`. The service layer canonicalizes each URL, scrapes all of them in parallel via the existing `ThreadPoolExecutor` pattern, and passes the concatenated article bodies to the summarizer layer.
- `_build_elaborate_prompt` keeps its three-section shape. The third section is renamed `<source-articles>` and contains all scraped article bodies concatenated (with per-article delimiters when length > 1). There is no branch on count.
- A new shared hook `useElaboration({ sourceMarkdown, articleUrls })` lives in `client/src/hooks/useElaboration.js` and owns the run/close/abort lifecycle and elaboration state. It is the only place in the client that posts to `/api/elaborate`.
- `ZenModeOverlay` calls `useElaboration({ sourceMarkdown: summaryMarkdown, articleUrls: [url] })`, defines the `Elaborate` action against the hook's `runElaboration`, passes the `overlayMenu` contract to `BaseOverlay`, and renders `<ElaborationPreview>` against the hook's state.
- `DigestOverlay` calls `useOverlayContextMenu(true)`, calls `useElaboration({ sourceMarkdown: digestMarkdown, articleUrls: digestArticleUrls })`, defines an `Elaborate` action with the same key/label/icon as Zen, passes the `overlayMenu` contract to `BaseOverlay`, and renders `<ElaborationPreview>` against the hook's state.
- `useDigest.js` exposes `markdown` and `articleUrls` alongside `html` so `DigestOverlay` can pass them through. Both values already exist on `data`.
- `App.jsx` passes `markdown` and `articleUrls` from `digest` into `DigestOverlay`.
- Docs describe Digest as a real menu consumer with an `Elaborate` action structurally identical to Zen's. The single difference is the size of the URL list it sends.

## What We Are Not Doing

- No Floating UI or BaseUI migration.
- No focus-stack or nested-layer ownership rewrite.
- No streaming response support for elaboration.
- No backend rate limiting, quota, or per-user gating.
- No prompt caching of any layer.
- No multi-action expansion of the menu beyond `Elaborate`. If/when more actions are added, that is its own scoping decision.
- No reuse of digest-cached elaborations across renders. Each `Elaborate` triggers a fresh fetch, same as Zen today.
- No `BaseOverlay` involvement in elaboration. The shell's contract surface stays the single `overlayMenu` prop introduced in plan 3.
- No backwards compatibility on the API. Old field names go away entirely; the lone client caller migrates in the same change.
- No new parallel scrape mechanism. The existing `ThreadPoolExecutor`-based helper is the only acceptable concurrency primitive for this work.
- No prompt structural redesign. Only the single section rename `<original-article>` → `<source-articles>` and per-article delimiters when the list has more than one entry.
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

Make the backend accept the new shape end-to-end. Always scrape, always build the same prompt. No frontend change yet.

### Changes Required

#### 1. Update the HTTP endpoint

**File**: `serve.py`

The endpoint should require `selected_text`, `source_markdown`, and `article_urls`. The docstring should describe the new shape and that `article_urls` must be a non-empty list.

#### 2. Update the application layer

**File**: `tldr_app.py`

Rename `elaborate_url` to `elaborate` and update its arg list to `(selected_text, source_markdown, article_urls, *, model)`. The response shape returns `elaboration_markdown` and `canonical_urls` (plural list of canonicalized URLs, in the same order as the input).

#### 3. Update the service layer

**File**: `tldr_service.py`

Rename `elaborate_url_content` to `elaborate_content`. Validate `selected_text` and `source_markdown` as non-empty. Validate `article_urls` is a non-empty list of non-empty strings. Canonicalize each URL.

Reuse the existing `_fetch_articles_content_parallel` pattern (`tldr_service.py:310-343`) to scrape all URLs in parallel. Either call that helper directly with placeholder title/category fields, or extract a thinner sibling helper that takes raw URLs and returns `dict[url, markdown]`. Pick whichever is the smaller diff.

If any individual scrape fails, surface a clear error rather than silently dropping the article. The elaboration's quality depends on having all the article bodies, so partial success is not acceptable for this path.

Pass `source_markdown` and the concatenated article bodies to `summarizer.elaborate`.

#### 4. Update the summarizer layer

**File**: `summarizer.py`

Rename `elaborate_url` to `elaborate`. Its signature becomes `(selected_text, source_markdown, article_bodies: list[str], *, model)`. Concatenate the article bodies with per-article delimiters when the list has more than one entry (e.g., a `<article index="N">...</article>` wrapper). When there is exactly one entry, no wrapper is needed.

`_build_elaborate_prompt` keeps its three-section structure. Rename the third section from `<original-article>` to `<source-articles>` to reflect plurality. Adjust the instructional preamble's wording to "Draw from the source articles to provide more depth" so it reads correctly for both N=1 and N>1.

Update the doctest to assert the renamed section name and to cover both the single-article and multi-article cases.

### Decision rationale

Renaming `summary_markdown` to `source_markdown` and `url` to `article_urls` is the disciplined choice. Keeping `summary_markdown` would force every Digest reader to mentally remap "summary" to "digest" forever; keeping `url` as a single field would either lie or accept dummy values from Digest callers. Renaming costs one frontend touchpoint and pays back permanently in clarity.

Making the list mandatory and non-empty is preferred over an optional field because it removes the prompt branch and the asymmetric quality story. Both consumers always provide article URLs; the backend always scrapes; the prompt is always the same shape.

Reusing `_fetch_articles_content_parallel` is preferred over inventing a new parallel mechanism because the parallel-scrape pattern, max-worker count, and error-handling shape are already a solved problem in this codebase. Inventing a parallel mechanism for the elaborate path would create two patterns to maintain.

Failing loudly on any individual scrape error is preferred over partial success because the user is waiting for an elaboration that depends on having full article context. A silently-dropped article would degrade quality without explanation.

### Verification

- `curl -X POST http://localhost:5001/api/elaborate -H 'Content-Type: application/json' -d '{"selected_text":"...","source_markdown":"...","article_urls":["https://..."]}'` returns `success: true` with `elaboration_markdown` and `canonical_urls`. Server logs show one Firecrawl call.
- `curl ... -d '{"selected_text":"...","source_markdown":"...","article_urls":["https://...","https://..."]}'` returns `success: true`. Server logs show two parallel Firecrawl calls.
- `curl ... -d '{"selected_text":"...","source_markdown":"...","article_urls":[]}'` returns 400 (empty list rejected).
- `curl ... -d '{"selected_text":"...","source_markdown":"..."}'` returns 400 (missing `article_urls`).
- Sending the legacy field names (`url`, `summary_markdown`) returns 400 — the rename is total.

## Phase 2: Extract The Shared Elaboration Hook

### Overview

Move Zen's elaboration lifecycle into a shared hook without changing visible Zen behavior.

### Changes Required

#### 1. Create `useElaboration`

**File**: `client/src/hooks/useElaboration.js` (new)

The hook accepts `{ sourceMarkdown, articleUrls }` (both required) and returns:

- `elaboration` — the state object (`status`, `selectedText`, `markdown`, `errorMessage`)
- `runElaboration(selectedText)` — fires the request, owns the `AbortController`, advances state through `loading → available | error`
- `closeElaboration()` — aborts the in-flight request, resets to idle

The hook should:

- Build the request body with `selected_text`, `source_markdown`, and `article_urls`.
- Trim selected text inside `runElaboration` so callers do not have to (matching the current Zen logic).
- Abort any in-flight request on unmount.

#### 2. Keep `ElaborationPreview` unchanged

**File**: `client/src/components/ElaborationPreview.jsx`

The component is already presentational and takes the right props. No changes here.

### Decision rationale

The hook returns the lifecycle primitives rather than composing the preview itself because consumers may want to render the preview at different points in their tree (for example, alongside other Zen-only or Digest-only siblings). Returning the data and giving the wrapper the render decision is the more flexible cut for two callers, and it keeps the hook a pure logic primitive.

The hook lives at `client/src/hooks/useElaboration.js` rather than next to `OverlayContextMenu` because elaboration is not a menu concern. The menu happens to invoke it; the hook itself is independent of the menu's existence.

`articleUrls` is a required prop, not optional. Both consumers always have URLs to send; allowing absence would re-introduce the branching the backend just removed.

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
  useElaboration({ sourceMarkdown: summaryMarkdown, articleUrls: [url] })
```

The `Elaborate` action body becomes a thin trampoline that calls `runElaboration(selectedText)`. The `<ElaborationPreview>` JSX reads from `elaboration` and calls `closeElaboration` on close.

The `useEffect` that aborted on unmount goes away because the hook owns abort-on-unmount.

#### 2. Confirm Zen behavior is identical

The visible Zen behavior should remain unchanged: right-click opens the menu, mobile selection opens the menu, `Elaborate` opens the preview with the captured selected text, escape and backdrop close the preview.

### Decision rationale

This phase is intentionally a behavior-preserving refactor. Holding it as its own phase makes regressions easy to spot — if Zen breaks here, the issue is in the hook extraction, not in the Digest wiring that follows.

Zen passes a one-element list. The list shape is the same shape Digest will use; the only difference is length. This symmetry is the point of the plan.

## Phase 4: Wire Digest As Menu Consumer

### Overview

Make `DigestOverlay` consume the menu surface contract from plan 3 and the elaboration hook from phase 2, with an `Elaborate` action identical to Zen's.

### Changes Required

#### 1. Expose digest markdown and article URLs from `useDigest`

**File**: `client/src/hooks/useDigest.js`

Add `markdown` and `articleUrls` to the hook's return object alongside `html`. Both values already exist as local computations on `data` (`articleCount` is derived from `data?.articleUrls?.length`, so `articleUrls` itself is already a known field shape).

#### 2. Pass markdown and articleUrls into `DigestOverlay`

**File**: `client/src/App.jsx`

Forward `markdown={digest.markdown}` and `articleUrls={digest.articleUrls}` in the conditional `<DigestOverlay />` render.

#### 3. Compose the menu and elaboration hooks in `DigestOverlay`

**File**: `client/src/components/DigestOverlay.jsx`

Add `markdown` and `articleUrls` props. Inside the component:

- Call `useOverlayContextMenu(true)`.
- Call `useElaboration({ sourceMarkdown: markdown, articleUrls })`.
- Define an `actions` array with a single `Elaborate` action whose `key`, `label`, `icon`, and trim-then-run behavior match Zen's exactly. The only difference is the closure capturing Digest's `runElaboration`.
- Build the `overlayMenu` contract object from the menu hook state and the action list.
- Pass the contract into `BaseOverlay`.
- Render `<ElaborationPreview>` against the elaboration hook's state.

The `Elaborate` action definition should be identical text and identical icon component — copy-paste, not abstraction. With only two callers, an "actions factory" abstraction is premature; the duplication is a few lines and signals the action's portability.

### Decision rationale

The `Elaborate` action being copy-pasted between Zen and Digest is intentional. The rule "actions are wrapper-owned" from plan 3 is preserved. If a third consumer ever appears, *then* extracting an `elaborateAction(runElaboration)` builder is the right move. Doing it now is an abstraction without a second example.

`DigestOverlay` passes a multi-element URL list. The hook accepts it without conditional code because the request shape always carries a list. Symmetry is the point.

### Verification

- Right-click inside the digest prose opens the menu.
- The menu shows `Elaborate` with the same icon and label as Zen.
- Selecting `Elaborate` opens `ElaborationPreview` with the digest's selected text and a coherent elaboration. Server logs show N parallel Firecrawl calls, where N is the digest's article count.
- Closing the digest while elaboration is in-flight aborts the request cleanly (verified via the AbortError log in `useElaboration`).
- Mobile text selection inside the digest opens the menu after finger lift, same as Zen.
- The `ElaborationPreview` Escape/backdrop dismissal works the same in Digest as in Zen.

## Phase 5: Update Documentation And Research Notes

### Overview

Reflect the new endpoint shape and the second menu consumer in the docs.

### Changes Required

#### 1. Update the API documentation in source comments and docstrings

**Files**: `serve.py`, `tldr_app.py`, `tldr_service.py`, `summarizer.py`

Each layer's docstring should describe the new arg names, the required non-empty `article_urls` list, the parallel-scrape semantics, and the renamed `<source-articles>` prompt section.

#### 2. Update the client docs

**Files**: `client/ARCHITECTURE.md`, `client/STATE_MACHINES.md`

Document that:

- `useElaboration` is a shared hook; both `ZenModeOverlay` and `DigestOverlay` instantiate it.
- The `Elaborate` action is consumer-defined but identical in shape across both overlays.
- `DigestOverlay` is now a menu consumer; the menu surface contract is fully shared.
- Zen sends a one-element URL list; Digest sends the digest's source URL list. The backend always scrapes all URLs in parallel.

#### 3. Update the research trail

**Files**: `thoughts/26-04-07-context-menu-research/0-b-feature-map.md`, `thoughts/26-04-07-context-menu-research/implementation/iteration-3.md` (or a new iteration file)

Update the feature map so it shows two consumers, the required `article_urls` list, and the parallel-scrape backend. Add an implementation log recording:

- the rename from `summary_markdown` / `url` to `source_markdown` / `article_urls`
- the prompt section rename from `<original-article>` to `<source-articles>`
- the reuse of `_fetch_articles_content_parallel`
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

1. `curl` with `selected_text`, `source_markdown`, and a one-element `article_urls` returns `success: true` with `elaboration_markdown` and `canonical_urls`. Server logs show one Firecrawl call.
2. `curl` with a multi-element `article_urls` returns `success: true`. Server logs show parallel Firecrawl calls (one per URL).
3. `curl` with empty `article_urls` returns 400.
4. `curl` with missing `article_urls` returns 400.
5. `curl` with the old field names (`summary_markdown`, `url`) returns 400.

#### Zen regression

1. Open a summary overlay, right-click in the prose, choose `Elaborate`.
2. Confirm the preview opens with the selected text and the elaboration draws on article-level depth (qualitative — should reference details that are in the article but compressed in the summary).
3. Confirm Escape closes preview only on first press, overlay only on second press.
4. Repeat on mobile selection.

#### Digest as a menu consumer

1. Trigger a digest from the selection dock.
2. Right-click in the digest prose; confirm the custom menu opens with `Elaborate`.
3. Choose `Elaborate`; confirm the preview opens with the selected text and a coherent elaboration that references the digest's framing AND draws on details from the underlying articles.
4. Confirm server logs show N parallel Firecrawl calls, where N is the digest's article count.
5. Close the digest while a slow elaboration is still loading; confirm the request aborts cleanly (the abort log fires; no stale response updates state).
6. On mobile, select text inside the digest; confirm the menu opens after finger lift.

#### Cross-consumer check

1. Open a Zen summary, run `Elaborate`, close it. Open a digest, run `Elaborate`, close it. Confirm neither overlay's elaboration state leaks into the other.

## Risk Notes

- The rename is total. There is no transitional period where both old and new field names work. The frontend and backend must ship together.
- Digest elaborations now scrape N articles per request. For typical digest sizes (2–10 articles) this is an acceptable latency and token-cost increase given the existing `max_workers=5` parallelism. If digests routinely exceed ~10 articles, latency may become noticeable; that is a future-tuning concern, not a blocker.
- Failing on any individual scrape error means a single broken source URL aborts the elaboration. This is intentional — partial-context elaborations would silently degrade quality. If a specific article URL is unreliable, it should be diagnosed at the source, not papered over here.
- `useElaboration` aborts on unmount. Digest unmounts when collapsed (per plan 3), so closing a digest mid-elaboration triggers the same abort path Zen uses. If plan 3's mount-lifecycle change has a regression, this plan will inherit it.
- Copy-pasting the `Elaborate` action between Zen and Digest is deliberate. Do not extract a builder yet; the second example is not enough signal for the right abstraction shape.
- The `markdown` and `articleUrls` exposure on `useDigest` is a small public-surface widening. Both values already exist on `data`; this just stops hiding them. No state-machine consequences.
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
