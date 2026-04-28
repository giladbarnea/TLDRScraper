---
originates_from: impl-review/0-g-review-1.md
last_updated: 2026-04-27 21:21, b387f55
implemented_by: implementation/3-define-shared-overlay-menu-contract-then-wire-digest.md
---

# Hoist Overlay Menu Surface Contract Into BaseOverlay; Align Digest Mount Lifecycle Implementation Plan

Implemented by: `implementation/3-define-shared-overlay-menu-contract-then-wire-digest.md`

## Overview

Implement the third item from `impl-review/0-g-review-1.md`: move the overlay-menu surface contract out of the current Zen-only integration shape and align `DigestOverlay`'s mount lifecycle with `ZenModeOverlay`. This plan does **not** wire Digest as a menu consumer; that step is deferred to `plans/3-b-generalize-elaborate-and-wire-digest.plan.md`, which also generalizes `/api/elaborate` so Digest can inherit Zen's `Elaborate` action without a bespoke action set.

The goal is not to make `BaseOverlay` own the menu state machine. The goal is to make `BaseOverlay` own the menu **surface contract** explicitly, because it already owns the portal shell, the scroll surface, the Escape close path, and the touch-gesture hooks the menu must coexist with.

This plan should land **after** `plans/2-make-mobile-selection-state-explicit.plan.md`. Do not fold the reducer work and the contract work into one change. The reducer plan made the mobile path smaller and calmer; this plan moves the now-clearer contract to its shared owner.

### Decision journey

This plan went through three shapes:

1. **Original**: hoist the contract into `BaseOverlay`, then wire Digest with placeholder actions like `Close digest` / `Mark digest done`. **Rejected**: those actions duplicate the header chevron and check buttons (`BaseOverlay.jsx:85-90` and `:94-99`). Adding them to a context menu is UI duplication, not a real consumer relationship.
2. **Counter-proposal**: collapse the Zen/Digest distinction by making `BaseOverlay` aware of Removables/Readables, so any overlay automatically gets the same menu actions. **Rejected**: pulls domain lifecycle into the shell. The right boundary keeps "what gets marked read/removed" as wrapper-owned callbacks, with the shell only owning the menu surface.
3. **Final (this plan)**: hoist the surface contract, align Digest's mount lifecycle with Zen, and defer Digest menu consumption until `/api/elaborate` is generalized so Digest can inherit Zen's actions undifferentiated.

The end-state product shape — Digest and Zen exposing the same context-menu actions — is the right one. Reaching it requires backend work that is intentionally out of scope here.

## Current State Analysis

The shared-vs-specific boundary is uneven, and the Digest mount lifecycle is asymmetric:

- `client/src/components/BaseOverlay.jsx:18`, `:46-52`, and `:112-116` contain menu-specific surface behavior even though the prop is still the loose `onContentContextMenu` handler.
- `client/src/components/ZenModeOverlay.jsx:16` and `:138-145` show that Zen still owns both menu state creation and menu rendering.
- `client/src/components/DigestOverlay.jsx:4-24` uses the same shared overlay shell but does not participate in the menu.
- `client/src/App.jsx:206-213` mounts `DigestOverlay` unconditionally, relying on `BaseOverlay.jsx:65` (`if (!expanded) return null`) to render nothing while the digest is collapsed. By contrast, `client/src/components/ArticleCard.jsx:224` only mounts `ZenModeOverlay` while the summary is open. This asymmetry is the practical reason the original plan-3 prescription — `useOverlayContextMenu(true)` in Digest — would attach document-level mobile-selection listeners while Digest is closed and could pick up selections inside Zen's `[data-overlay-content]` surface.
- `client/src/hooks/useOverlayContextMenu.js:33-91` already gives a per-overlay state owner after the desktop/mobile split. That work is reused, not reopened.

The documentation already describes the menu as a shared overlay primitive rather than a Zen-only feature:

- `client/ARCHITECTURE.md:177-199` says the menu is intended for both `ZenModeOverlay` and `DigestOverlay`.
- `client/STATE_MACHINES.md:564-599` and `:841-905` describe Digest as the planned second consumer.
- `client/STATE_MACHINES.md:720-766` already frames `BaseOverlay` as the shared foundation that owns the relevant surface.

A product constraint forces the deferral:

- `/api/elaborate` is single-summary specific in `serve.py:152-166`, `tldr_app.py:70-89`, and `tldr_service.py:439-458`.
- It requires `url`, `selected_text`, and `summary_markdown`. Digest synthesizes markdown from multiple URLs, so it cannot reuse Zen's `Elaborate` action without a separate backend generalization.

## Key Discoveries

- The real problem is not that `BaseOverlay` knows about the menu at all. The real problem is that it knows about the menu **implicitly** while Zen owns the visible integration **concretely**.
- `BaseOverlay` is the right owner for the contract because it already owns the only DOM node that can honestly promise "`data-overlay-content` means this overlay's reading surface."
- Once `DigestOverlay` is conditionally mounted, the `expanded` prop on `BaseOverlay` (`:14, :38, :42, :65`) becomes vestigial. All three readers collapse to "always render" once mount-vs-unmount is the only visibility toggle. This is a net deletion the conditional-mount move enables.
- The already-landed `useOverlayContextMenu` split means the shared contract can stay small: `BaseOverlay` owns surface wiring; each wrapper still owns its own hook instance and action list.
- Wiring Digest with placeholder actions is net UI duplication. Wiring Digest with generic `Elaborate` requires backend generalization. Either is the wrong size for this plan.

## Desired End State

After this plan is implemented:

- `DigestOverlay` is mounted only while `digest.expanded` is true, mirroring how `ArticleCard` mounts `ZenModeOverlay`.
- The `expanded` prop is removed from both `BaseOverlay` and `DigestOverlay`. If a `BaseOverlay` is mounted, it is open.
- `BaseOverlay` accepts one explicit optional menu contract prop, for example `overlayMenu`.
- When `overlayMenu` is present, `BaseOverlay` owns all surface-level menu participation:
  - the `data-overlay-content` marker
  - the scroll-surface `onContextMenu` binding
  - rendering `OverlayContextMenu` with the provided state, refs, and actions
- When `overlayMenu` is absent, `BaseOverlay` renders as a plain overlay shell with no menu-specific surface markers or handlers.
- `ZenModeOverlay` passes the shared contract into `BaseOverlay`, keeps the existing `Elaborate` action, and keeps `ElaborationPreview` fully Zen-owned.
- `DigestOverlay` does **not** consume the menu contract in this plan. It remains menu-free until a follow-up plan generalizes `/api/elaborate`.
- The docs describe the contract as fully shared, name `BaseOverlay` as its owner, and explicitly call out that Digest does not yet consume the menu.

## What We Are Not Doing

- No desktop/mobile path split work. That belongs to plan 1 and is already present in the current hook shape.
- No mobile selection reducer work. That belongs to plan 2.
- No Floating UI or BaseUI migration.
- No focus-stack or nested-layer ownership rewrite. Escape arbitration stays as-is in this phase.
- No pull-to-close restoration.
- No `zenLock` changes.
- No Digest menu wiring of any kind: no placeholder actions like `Close digest` / `Mark digest done`, and no Digest-side `useOverlayContextMenu` instance.
- No `/api/elaborate` generalization. Digest elaboration is its own follow-up plan.
- No attempt to make `BaseOverlay` own domain lifecycle (Removables/Readables). Wrapper-owned callbacks remain the boundary.

## Implementation Approach

Use a single explicit contract object on `BaseOverlay` rather than another loose boolean-plus-handler pairing.

Conceptually, the shared contract should look like this:

```text
overlayMenu
  state:
    isOpen
    anchorX
    anchorY
    selectedText
    menuRef
  handlers:
    handleContextMenu
    closeMenu
  actions:
    action[]
```

The important boundary is:

- `useOverlayContextMenu` remains the per-overlay state owner.
- `BaseOverlay` becomes the single owner of menu-surface wiring.
- Each wrapper remains the owner of its own action semantics.

That gives the project one stable layering rule:

```text
wrapper owns menu state + actions
BaseOverlay owns menu surface contract + menu render site
```

This is the smallest change that resolves the "half-expressed shared contract" problem without forcing backend work or inventing throwaway Digest actions.

## Phase 1: Align Digest Mount Lifecycle With Zen

### Overview

Make `DigestOverlay` mount only while open. Remove the now-vestigial `expanded` prop from `BaseOverlay` and `DigestOverlay`.

### Why first

The original plan-3 prescription — `useOverlayContextMenu(true)` in `DigestOverlay` — would attach document-level mobile-selection listeners while the digest is closed because `DigestOverlay` is currently always mounted. Even though this plan no longer wires Digest as a menu consumer, the asymmetry is a real smell on its own and would block any future Digest menu wiring. Fixing it first also enables the `expanded` prop deletion.

### Changes Required

#### 1. Conditionally render `DigestOverlay` in `App.jsx`

**File**: `client/src/App.jsx`

Wrap the `DigestOverlay` render so it only mounts while `digest.expanded` is true. This mirrors the `summary.expanded && <ZenModeOverlay ... />` pattern in `ArticleCard.jsx`.

#### 2. Remove the `expanded` prop from `DigestOverlay`

**File**: `client/src/components/DigestOverlay.jsx`

Once Digest is only mounted while open, the prop has no remaining purpose. Stop forwarding it.

#### 3. Remove the `expanded` prop from `BaseOverlay`

**File**: `client/src/components/BaseOverlay.jsx`

Drop the prop, the default value, the `if (!expanded) return null` early return, and the `expanded` arguments to `useScrollProgress` and `useOverscrollUp`. Replace the body-overflow effect's `expanded` gate with the implicit invariant "if this component is mounted, the overlay is open."

`useScrollProgress` and `useOverscrollUp` will reset on mount and tear down on unmount, which is the correct lifecycle once mount-vs-unmount is the only visibility toggle.

### Decision rationale

Keeping the `expanded` prop after conditional mount would leave a dead branch that future readers must reason about. The plan's brief is to reduce complexity, not to leave half-disabled mechanisms in place.

## Phase 2: Formalize The Shared Contract In BaseOverlay

### Overview

Replace the ad hoc `onContentContextMenu` integration with one explicit shared menu contract prop on `BaseOverlay`.

### Changes Required

#### 1. Replace the loose prop with an explicit contract object

**File**: `client/src/components/BaseOverlay.jsx`

Replace the surface-level prop shape from:

- `onContentContextMenu`

to a single optional prop such as:

- `overlayMenu`

This prop is the feature boundary. If it is missing, `BaseOverlay` behaves like a plain overlay shell. If it is present, `BaseOverlay` opts into the menu surface contract.

#### 2. Move the render site for `OverlayContextMenu` into `BaseOverlay`

**Files**:

- `client/src/components/BaseOverlay.jsx`
- `client/src/components/OverlayContextMenu.jsx`

`OverlayContextMenu` itself stays presentational. The important change is its render site:

- `ZenModeOverlay` stops rendering it directly.
- `BaseOverlay` renders it when `overlayMenu` is present.

The shared overlay shell becomes the one place that owns the selectable surface and the menu attached to that surface.

#### 3. Make surface participation conditional and explicit

**File**: `client/src/components/BaseOverlay.jsx`

When `overlayMenu` is present:

- attach `overlayMenu.handleContextMenu` to the scroll surface
- add `data-overlay-content` to that same scroll surface
- render `OverlayContextMenu` with the provided state and actions

When `overlayMenu` is absent:

- do not attach the context-menu handler
- do not stamp the surface with the menu marker
- do not render the menu component

This is the actual "co-locate the contract" move. The contract becomes "pass the explicit menu surface prop" instead of "remember that this generic prop plus a hardcoded marker plus a comment block must stay aligned."

### Decision rationale

A single optional contract object is preferred over a flag-plus-handler pair so the surface either fully opts in or stays plain — there is no "partially wired" state to misuse later.

#### 4. Keep Escape arbitration behavior intact in this phase

**File**: `client/src/components/BaseOverlay.jsx`

Do not redesign the Escape ownership model here. Keep the existing `event.defaultPrevented` guard and update its surrounding comment so it refers to the explicit `overlayMenu` contract rather than the current hidden handshake.

This plan is about making the shared contract explicit, not about solving the later stack/focus problem from item 5 in the review.

## Phase 3: Move Zen To The Explicit Contract

### Overview

Adopt the new `BaseOverlay` contract from Zen without changing Zen's elaboration behavior.

### Changes Required

#### 1. Stop rendering `OverlayContextMenu` directly in Zen

**File**: `client/src/components/ZenModeOverlay.jsx`

Keep:

- `useOverlayContextMenu(true)`
- Zen-owned action definitions
- Zen-owned elaboration fetch lifecycle
- Zen-owned `ElaborationPreview`

Change only the integration shape:

- build the `overlayMenu` object from the hook state and Zen's actions
- pass that object into `BaseOverlay`
- delete the sibling `<OverlayContextMenu>` render from `ZenModeOverlay`

The visible Zen behavior should remain unchanged:

- right-click still opens the menu
- mobile selection still opens the menu
- `Elaborate` still uses captured selected text
- `ElaborationPreview` still sits above the overlay as a Zen-only layer

#### 2. Keep Zen-specific elaboration semantics out of the shared contract

**File**: `client/src/components/ZenModeOverlay.jsx`

Do not push any of the following into `BaseOverlay`:

- `/api/elaborate` request logic
- `AbortController` ownership
- elaboration idle/loading/available/error state
- `ElaborationPreview`

Those are Zen domain behaviors, not shared overlay-surface behaviors.

### Decision rationale

The boundary between "menu surface" (shared) and "what an action does" (wrapper-owned) is the only seam that survives both the current Zen-only state and a future Digest menu consumer. Pushing elaboration any deeper would force a rewrite when Digest's elaboration semantics are eventually wired in.

## Phase 4: Update Documentation And Research Notes

### Overview

Update the docs so the codebase description matches reality and so the deferred Digest menu work is recorded as such.

### Changes Required

#### 1. Update the client docs

**Files**:

- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`

Document that:

- `BaseOverlay` owns the explicit overlay-menu surface contract.
- `BaseOverlay` mounts only while open; the `expanded` prop no longer exists.
- `ZenModeOverlay` is the only current consumer of the menu contract.
- `OverlayContextMenu` is rendered through the shared shell when the contract is present.
- Action sets are wrapper-owned and can differ between overlays when consumers are added.
- `DigestOverlay` does not yet consume the menu contract, and will not until `/api/elaborate` is generalized to support digest-shaped contexts.

Remove phrasing that implies Digest is wired in this iteration.

#### 2. Update the research trail

**Files**:

- `thoughts/26-04-07-context-menu-research/0-b-feature-map.md`
- `thoughts/26-04-07-context-menu-research/implementation/iteration-3.md`

Update the feature map so it reflects the new ownership boundary:

- BaseOverlay owns the menu surface contract and is mounted only while open.
- Zen owns elaboration behavior and is the lone menu consumer for now.
- Digest mount lifecycle now matches Zen; menu consumption is deferred.

Add a short implementation log that records:

- what contract moved
- which files became thinner
- the `expanded` prop deletion
- the explicit deferral of Digest menu wiring and its dependency on `/api/elaborate` generalization

Do not manually edit YAML timestamp fields.

## Acceptance Criteria

### Automated Verification

- [ ] `cd client && npm run build`
- [ ] `cd client && CI=1 npm run lint`
- [ ] `rg -n "useOverlayContextMenu\\(" client/src/components`
  Expected: only `ZenModeOverlay.jsx`. Digest is intentionally not a consumer in this plan.
- [ ] `rg -n "OverlayContextMenu" client/src/components`
  Expected: `BaseOverlay.jsx` is the render site; `ZenModeOverlay.jsx` no longer renders it directly.
- [ ] `rg -n "onContentContextMenu" client/src`
  Expected: old loose prop is removed.
- [ ] `rg -n "data-overlay-content" client/src/components/BaseOverlay.jsx`
  Expected: the marker remains in one explicit shared location.
- [ ] `rg -n "expanded" client/src/components/BaseOverlay.jsx client/src/components/DigestOverlay.jsx`
  Expected: the prop is gone from both files.

Only fix build or lint failures introduced by this work.

### Manual Verification

#### Zen

1. Open a summary overlay.
2. Right-click inside the prose body and confirm the custom menu opens.
3. Choose `Elaborate` and confirm the existing preview still opens with the selected text.
4. Press Escape once and confirm only the menu closes.
5. Press Escape again and confirm the overlay closes.
6. On mobile or emulation, select text and confirm the menu still opens after finger lift.

#### Digest

1. Trigger a digest from the selection dock and confirm it opens normally.
2. Confirm right-click inside the digest prose does **not** open a custom menu (Digest is not a consumer in this plan; the native menu is acceptable).
3. Close the digest with the chevron-down and confirm `digest.collapse(false)` runs.
4. Reopen and close with the check button and confirm `digest.collapse(true)` runs the mark-removed lifecycle.

#### Scroll / pull regression after the mount-lifecycle change

The single load-bearing behavior for whether the `expanded` deletion was clean:

1. Open the digest, pull content upward past the threshold, and confirm the green check completes and `onMarkRemoved` fires.
2. Close the digest and reopen it. Repeat the pull-up gesture and confirm it still completes correctly. This is the litmus test for whether `useOverscrollUp` and `useScrollProgress` survived the shift from "always mounted, gated by `expanded`" to "mounted only while open."
3. Confirm the top scroll progress bar updates while scrolling the prose on a freshly mounted digest.

#### General regression checks

1. Confirm `ElaborationPreview` still closes independently via Escape and backdrop.
2. Confirm Digest still respects the one-overlay-at-a-time lock.
3. Confirm `BaseOverlay` still behaves normally when used without a menu contract in any future or incidental consumer.
4. Confirm menu clicks still do not bubble through and trigger the underlying article card.

## Risk Notes

- Do not combine this refactor with the mobile reducer plan. The two changes touch the same seams for different reasons.
- Moving the menu render site into `BaseOverlay` is structural. Keep `OverlayContextMenu` itself as stable as possible so behavior stays boring while ownership changes.
- The `expanded` prop deletion is a real lifecycle change for Digest. The scroll/pull regression check above is the single behavior that proves it landed cleanly.
- Deferring Digest menu wiring is deliberate. The placeholder-actions path was rejected because those actions duplicate the header buttons. The "make `BaseOverlay` know Removables/Readables" path was rejected because it pulls domain lifecycle into the shell. Both rejections are recorded so a future contributor does not re-derive them under time pressure.
- Generalizing `/api/elaborate` for Digest is a separate plan. Do not stretch this one.
- The later focus-stack / BaseUI work should see a clearer system after this change, because the shared surface contract will already be localized.

## References

- `thoughts/26-04-07-context-menu-research/impl-review/0-g-review-1.md`
- `thoughts/26-04-07-context-menu-research/plans/1-split-mobile-and-desktop.plan.md`
- `thoughts/26-04-07-context-menu-research/plans/2-make-mobile-selection-state-explicit.plan.md`
- `thoughts/26-04-07-context-menu-research/plans/3-b-generalize-elaborate-and-wire-digest.plan.md`
- `thoughts/26-04-07-context-menu-research/0-b-feature-map.md`
- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`
- `client/src/App.jsx`
- `client/src/components/ArticleCard.jsx`
- `client/src/components/BaseOverlay.jsx`
- `client/src/components/ZenModeOverlay.jsx`
- `client/src/components/DigestOverlay.jsx`
- `client/src/components/OverlayContextMenu.jsx`
- `client/src/components/ElaborationPreview.jsx`
- `client/src/hooks/useOverlayContextMenu.js`
- `client/src/hooks/useDigest.js`
- `serve.py`
- `tldr_app.py`
- `tldr_service.py`
