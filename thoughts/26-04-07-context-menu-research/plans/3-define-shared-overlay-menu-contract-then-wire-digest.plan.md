---
originates_from: impl-review/review-1.md
last_updated: 2026-04-23 20:31
---

# Define Shared Overlay Menu Contract Then Wire Digest Implementation Plan

## Overview

Implement the third item from `impl-review/review-1.md`: move the overlay-menu contract out of the current Zen-only integration shape and make `DigestOverlay` a real consumer of the same shared contract.

The goal is not to make `BaseOverlay` own the menu state machine. The goal is to make `BaseOverlay` own the menu **surface contract** explicitly, because it already owns the portal shell, the scroll surface, the Escape close path, and the touch-gesture hooks that the menu must coexist with.

This plan should land **after** `plans/2-make-mobile-selection-state-explicit.plan.md`. Do not fold the reducer work and the contract work into one change. The reducer plan makes the mobile path smaller and calmer; this plan then moves the now-clearer contract to its shared owner.

## Current State Analysis

Today the shared-vs-specific boundary is still uneven:

- `client/src/components/BaseOverlay.jsx:18`, `client/src/components/BaseOverlay.jsx:46-52`, and `client/src/components/BaseOverlay.jsx:112-116` contain menu-specific surface behavior even though the prop is still the loose `onContentContextMenu` handler.
- `client/src/components/ZenModeOverlay.jsx:16` and `client/src/components/ZenModeOverlay.jsx:138-145` show that Zen still owns both menu state creation and menu rendering.
- `client/src/components/DigestOverlay.jsx:4-24` uses the same shared overlay shell but does not participate in the menu at all.
- `client/src/hooks/useOverlayContextMenu.js:27-76` and `client/src/hooks/useOverlayContextMenu.js:79-210` already give us a good per-overlay state owner after the desktop/mobile split. That work should be reused, not reopened.

The documentation already describes the menu as a shared overlay primitive rather than a Zen-only feature:

- `client/ARCHITECTURE.md:177-199` says the menu is intended for both `ZenModeOverlay` and `DigestOverlay`.
- `client/STATE_MACHINES.md:564-599` and `client/STATE_MACHINES.md:841-905` describe Digest as the planned second consumer.
- `client/STATE_MACHINES.md:720-766` already frames `BaseOverlay` as the shared foundation that owns the relevant surface.

There is also a product constraint that matters for scoping:

- `/api/elaborate` is still single-summary specific in `serve.py:152-166`, `tldr_app.py:70-89`, and `tldr_service.py:439-458`.
- It requires `url`, `selected_text`, and `summary_markdown`, so Digest cannot simply reuse Zen's `Elaborate` action without separate backend work.

## Key Discoveries

- The real problem is not that `BaseOverlay` knows about the menu at all. The real problem is that it knows about the menu **implicitly** while Zen owns the visible integration **concretely**.
- `BaseOverlay` is the right owner for the contract because it already owns the only DOM node that can honestly promise "`data-overlay-content` means this overlay's reading surface."
- The already-landed `useOverlayContextMenu` split means the shared contract can stay small: BaseOverlay owns surface wiring, while each wrapper still owns its own hook instance and action list.
- Digest should become a real consumer in this phase, but it should do so using actions its current client/backend model already supports. Extending digest elaboration is a separate effort.

## Desired End State

After this plan is implemented:

- `BaseOverlay` accepts one explicit optional menu contract prop, for example `overlayMenu`.
- When `overlayMenu` is present, `BaseOverlay` owns all surface-level menu participation:
  - the `data-overlay-content` marker
  - the scroll-surface `onContextMenu` binding
  - rendering `OverlayContextMenu` with the provided state, refs, and actions
- When `overlayMenu` is absent, `BaseOverlay` renders as a plain overlay shell with no menu-specific surface markers or handlers.
- `ZenModeOverlay` passes the shared contract into `BaseOverlay`, keeps the existing `Elaborate` action, and keeps `ElaborationPreview` fully Zen-owned.
- `DigestOverlay` passes the same contract shape into `BaseOverlay` and exposes only digest-safe actions in this phase.
- The docs stop describing Digest as a merely planned consumer and instead describe the contract as fully shared, with overlay-specific action sets layered on top.

## What We Are Not Doing

- No desktop/mobile path split work. That belongs to plan 1 and is already present in the current hook shape.
- No mobile selection reducer work. That belongs to plan 2.
- No Floating UI or BaseUI migration.
- No focus-stack or nested-layer ownership rewrite. Escape arbitration stays as-is in this phase.
- No pull-to-close restoration.
- No `zenLock` changes.
- No digest elaboration backend or `/api/elaborate` expansion.
- No attempt to make Zen and Digest share an identical action list.

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

This is the smallest change that actually resolves the "half-expressed shared contract" problem.

## Phase 1: Formalize The Shared Contract In BaseOverlay

### Overview

Replace the current ad hoc `onContentContextMenu` integration with one explicit shared menu contract prop on `BaseOverlay`.

### Changes Required

#### 1. Replace the loose prop with an explicit contract object

**File**: `client/src/components/BaseOverlay.jsx`

Replace the surface-level prop shape from:

- `onContentContextMenu`

to a single optional prop such as:

- `overlayMenu`

This prop should be the feature boundary. If it is missing, `BaseOverlay` behaves like a plain overlay shell. If it is present, `BaseOverlay` opts into the menu surface contract.

#### 2. Move the render site for `OverlayContextMenu` into `BaseOverlay`

**Files**:

- `client/src/components/BaseOverlay.jsx`
- `client/src/components/OverlayContextMenu.jsx`

`OverlayContextMenu` itself can stay a presentational component. The important change is its render site:

- `ZenModeOverlay` should stop rendering it directly.
- `BaseOverlay` should render it when `overlayMenu` is present.

This makes the shared overlay shell the one place that owns the selectable surface and the menu attached to that surface.

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

#### 4. Keep Escape arbitration behavior intact in this phase

**File**: `client/src/components/BaseOverlay.jsx`

Do not redesign the Escape ownership model here. Keep the existing `event.defaultPrevented` guard and update its surrounding comment so it refers to the explicit `overlayMenu` contract rather than the current hidden handshake.

This plan is about making the shared contract explicit, not about solving the later stack/focus problem from item 5 in the review.

## Phase 2: Move Zen To The Explicit Contract

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

## Phase 3: Wire Digest Through The Same Contract

### Overview

Make `DigestOverlay` the second real consumer of the shared menu contract, using only actions that are already supported by the current client behavior.

### Changes Required

#### 1. Give Digest its own `useOverlayContextMenu` instance

**File**: `client/src/components/DigestOverlay.jsx`

Instantiate the same hook that Zen uses:

- `useOverlayContextMenu(true)`

Digest should not get a bespoke menu hook or a simplified one-off integration. The whole point of this phase is that Digest becomes an instance of the same contract.

#### 2. Use digest-safe actions only

**Files**:

- `client/src/components/DigestOverlay.jsx`
- no backend changes expected

Because `/api/elaborate` is single-summary specific, Digest should not expose `Elaborate` in this phase.

Instead, wire Digest with actions that are already valid for the digest overlay today:

- `Close digest` → delegate to the existing `onClose`
- `Mark digest done` → delegate to the existing `onMarkRemoved`

These actions are intentionally boring. They make Digest a real consumer of the shared menu contract without turning this plan into backend work or inventing a second bespoke elaboration flow.

If the action schema passes `selectedText` into each action callback, Digest's actions may simply ignore it. The action interface stays shared even when the semantics differ by overlay.

#### 3. Pass the same contract object into `BaseOverlay`

**File**: `client/src/components/DigestOverlay.jsx`

Digest should pass the same conceptual shape that Zen passes:

```text
overlayMenu = {
  hook state,
  closeMenu,
  handleContextMenu,
  menuRef,
  selectedText,
  digest actions,
}
```

That should be the only new surface-level wiring Digest needs.

#### 4. Keep `useDigest` and `App.jsx` unchanged unless the new action wiring exposes a real gap

**Files**:

- `client/src/hooks/useDigest.js`
- `client/src/App.jsx`

The current digest lifecycle already supplies the needed commands:

- `onClose={() => digest.collapse(false)}`
- `onMarkRemoved={() => digest.collapse(true)}`

This plan should reuse those handlers through `DigestOverlay` rather than reaching deeper into digest state from the menu layer.

If either handler proves semantically wrong for the menu action labels, fix the label or the wrapper-level delegation first. Do not push menu-aware branches down into `useDigest`.

## Phase 4: Update Documentation And Research Notes

### Overview

Once the contract and Digest wiring work, update the docs so the codebase description matches reality.

### Changes Required

#### 1. Update the client docs

**Files**:

- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`

Document that:

- `BaseOverlay` owns the explicit overlay-menu surface contract
- `ZenModeOverlay` and `DigestOverlay` are both consumers
- `OverlayContextMenu` is rendered through the shared shell when the contract is present
- action sets are wrapper-owned and can differ between overlays
- Digest does not yet support selected-text elaboration

The old phrasing that Digest is only a "planned second consumer" should be removed.

#### 2. Update the research trail

**Files**:

- `thoughts/26-04-07-context-menu-research/feature-map.md`
- `thoughts/26-04-07-context-menu-research/implementation/iteration-3.md`

Update the feature map so it reflects the new ownership boundary:

- BaseOverlay owns the menu surface contract
- Zen owns elaboration behavior
- Digest owns digest-safe actions on the same menu primitive

Add a short implementation log that records:

- what contract moved
- which files became thinner
- what Digest now supports
- what remains intentionally deferred, especially digest elaboration and the later focus-stack work

Do not manually edit YAML timestamp fields.

## Acceptance Criteria

### Automated Verification

- [ ] `cd client && npm run build`
- [ ] `cd client && CI=1 npm run lint`
- [ ] `rg -n "useOverlayContextMenu\\(" client/src/components`
  Expected: both `ZenModeOverlay.jsx` and `DigestOverlay.jsx`
- [ ] `rg -n "OverlayContextMenu" client/src/components`
  Expected: `BaseOverlay.jsx` becomes the render site; `ZenModeOverlay.jsx` no longer renders it directly
- [ ] `rg -n "onContentContextMenu" client/src`
  Expected: old loose prop is removed
- [ ] `rg -n "data-overlay-content" client/src/components/BaseOverlay.jsx`
  Expected: the marker remains in one explicit shared location

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

1. Select multiple articles and open a digest.
2. Right-click inside the digest prose and confirm the custom menu opens.
3. Choose `Close digest` and confirm the digest closes without affecting unrelated state.
4. Reopen the digest, open the menu again, choose `Mark digest done`, and confirm it triggers the same lifecycle as the existing header check action.
5. On mobile or emulation, select text inside the digest and confirm the menu opens through the same surface contract.
6. Tap outside the menu and confirm the menu closes and native selection clears when applicable.

#### Regression Checks

1. Confirm `ElaborationPreview` still closes independently via Escape and backdrop.
2. Confirm Digest still respects the one-overlay-at-a-time lock.
3. Confirm BaseOverlay still behaves normally when used without a menu contract in any future or incidental consumer.
4. Confirm menu clicks still do not bubble through and trigger the underlying article card.

## Risk Notes

- Do not combine this refactor with the mobile reducer plan. The two changes touch the same seams for different reasons.
- Moving the menu render site into `BaseOverlay` is structural. Keep `OverlayContextMenu` itself as stable as possible so behavior stays boring while ownership changes.
- Digest actions ignoring `selectedText` are deliberate in this phase. That is a scoping choice, not a bug.
- The existing backend contract makes digest elaboration a separate feature. If that capability is later desired, give it its own plan instead of quietly stretching this one.
- The later focus-stack / BaseUI work should see a clearer system after this change, because the shared surface contract will already be localized.

## References

- `thoughts/26-04-07-context-menu-research/impl-review/review-1.md`
- `thoughts/26-04-07-context-menu-research/plans/1-split-mobile-and-desktop.plan.md`
- `thoughts/26-04-07-context-menu-research/plans/2-make-mobile-selection-state-explicit.plan.md`
- `thoughts/26-04-07-context-menu-research/feature-map.md`
- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`
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
