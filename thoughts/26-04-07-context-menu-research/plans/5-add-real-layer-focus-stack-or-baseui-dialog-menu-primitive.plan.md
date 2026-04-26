---
originates_from: impl-review/0-g-review-1.md
last_updated: 2026-04-26 07:29
---

# Add Real Layer/Focus Stack Implementation Plan

## Overview

Implement the fifth item from `impl-review/0-g-review-1.md`: replace per-layer Escape arbitration with one real overlay layer stack. The goal is that the topmost active layer owns Escape, outside-pointer dismissal, and focus behavior, so `BaseOverlay`, `OverlayContextMenu`, and `ElaborationPreview` stop coordinating through `event.defaultPrevented`, capture-phase listener order, and `stopImmediatePropagation()`.

This plan deliberately chooses a small project-owned layer/focus stack instead of BaseUI dialog/menu primitives. BaseUI remains a good final destination, but the review already keeps "Full BaseUI migration" as item 7. Pulling BaseUI into this step would combine stack semantics, menu/dialog replacement, focus behavior, and dependency migration at once. The smaller move is to define the stack contract locally now, prove the semantics against the existing overlay/menu/preview layers, and leave a later BaseUI migration with an explicit behavior target.

This plan should land after `plans/4-introduce-floating-ui-for-positioning-only.plan.md` if the recommended order is followed. It does not depend on positioning details, though. If plan 4 has not landed by implementation time, do not bundle positioning changes into this work.

## Current State Analysis

The current checked-in code has three independent layer-level keyboard systems:

- `BaseOverlay` installs its own document `keydown` listener and closes on Escape unless `event.defaultPrevented` is set in `client/src/components/BaseOverlay.jsx:43`.
- `useOverlayContextMenu` installs document-level pointer and Escape listeners while the menu is open in `client/src/hooks/useOverlayContextMenu.js:200`. Its Escape path calls `preventDefault()`, `stopPropagation()`, and `stopImmediatePropagation()` in `client/src/hooks/useOverlayContextMenu.js:216`.
- `ElaborationPreview` installs another capture-phase document `keydown` listener while open in `client/src/components/ElaborationPreview.jsx:60`.

That means layer priority is implicit in listener timing and propagation side effects. It currently works because the menu closes before preview opens, and because `BaseOverlay` yields when the menu marks the event as prevented. It is not a durable model for nested layers.

Focus is also distributed:

- `OverlayContextMenu` manually focuses the first action on desktop in `client/src/components/OverlayContextMenu.jsx:21`.
- `ElaborationPreview` declares `role="dialog"` and `aria-modal="true"` in `client/src/components/ElaborationPreview.jsx:91`, but it does not trap focus or restore focus.
- `BaseOverlay` is a full-screen modal shell at `client/src/components/BaseOverlay.jsx:65`, but its keyboard ownership and focus behavior are separate from the menu and preview layers.

The shared menu surface contract from plan 3 is already in place:

- `ZenModeOverlay` owns `useOverlayContextMenu(true)` and passes `overlayMenu` into `BaseOverlay` in `client/src/components/ZenModeOverlay.jsx:107`.
- `BaseOverlay` owns `data-overlay-content`, the surface `onContextMenu`, and the `OverlayContextMenu` render site in `client/src/components/BaseOverlay.jsx:102`.
- `DigestOverlay` composes `BaseOverlay` but does not yet pass `overlayMenu` in `client/src/components/DigestOverlay.jsx:4`.
- `App` mounts `DigestOverlay` only while `digest.expanded` is true in `client/src/App.jsx:206`.

The plan must preserve the portal-bubbling fix:

- `BaseOverlay`, `OverlayContextMenu`, and `ElaborationPreview` all render through portals. Portal clicks still bubble through the React tree, so the root `onClick={(e) => e.stopPropagation()}` guards must stay. This is why menu/preview clicks do not ghost-click `ArticleCard`, whose click handler opens/closes summaries in `client/src/components/ArticleCard.jsx:117`.

## Desired End State

After implementation:

- The app has a single `OverlayLayerProvider` mounted once near the app root.
- Layers register themselves with a semantic priority and callbacks:
  - Reader overlay layer: `BaseOverlay`
  - Context menu layer: `OverlayContextMenu`
  - Dialog layer: `ElaborationPreview`
- The topmost registered layer owns Escape. No layer calls `stopImmediatePropagation()` to beat another layer.
- `BaseOverlay`, `OverlayContextMenu`, and `ElaborationPreview` no longer install their own document Escape listeners.
- The context menu's outside-pointer dismissal is routed through the same top-layer stack, so only the topmost layer responds to global pointer dismissal.
- Focus behavior is explicit:
  - `BaseOverlay` restores focus on close and contains keyboard focus within the full-screen reader shell.
  - `OverlayContextMenu` focuses its first action when opened and contains keyboard focus while the menu is open.
  - `ElaborationPreview` focuses its close button, traps focus inside the dialog panel, and restores focus when closed.
- Existing visual layering and z-index classes remain unchanged.
- Existing product behavior remains unchanged from the user's perspective:
  - Escape on a plain reader overlay closes the reader.
  - Escape while menu is open closes only the menu.
  - Escape while elaboration preview is open closes only the preview.
  - Pressing Escape again then closes the next layer down.
  - Menu outside pointer closes the menu and clears native selection only for mobile-selection-opened menus.

## Key Discoveries

- React context crosses portals, so a provider mounted in `App` can serve `BaseOverlay`, `OverlayContextMenu`, and `ElaborationPreview` even though they portal to `document.body`.
- A stack is a better fit than local keydown listeners because the layer order is semantic, not incidental. The menu is visually above the reader; the preview is visually above both. That should be represented directly.
- `ToastContainer` uses `z-[300]` in `client/src/components/ToastContainer.jsx:69`, but toasts are notifications, not modal layers. They should not register with the stack or own Escape/focus.
- A local stack does not block BaseUI later. It creates a crisp behavior contract that BaseUI components must preserve when the full migration happens.

## What We Are Not Doing

- No BaseUI migration in this plan.
- No Floating UI positioning work. That belongs to plan 4.
- No Digest menu wiring or `/api/elaborate` generalization. That belongs to `plans/3-b-generalize-elaborate-and-wire-digest.plan.md`.
- No pull-to-close restoration.
- No changes to the mobile selection reducer transitions.
- No visual redesign of `OverlayContextMenu`, `BaseOverlay`, or `ElaborationPreview`.
- No action-set changes.
- No `zenLock` changes.
- No toast layer registration.
- No broad cleanup of `[ctxmenu]` or `[elaborate]` debug logs unless a touched line must change for the stack integration.

## Implementation Approach

Add a small layer-stack context and hook. The stack should own only cross-layer behavior: topmost Escape, topmost outside-pointer dismissal, focus entry, focus containment, and focus restoration. Domain behavior stays where it already lives:

- `BaseOverlay` still owns close and mark-removed callbacks.
- `useOverlayContextMenu` still owns menu state, selected text, mobile reducer reset, and whether outside dismissal should clear native selection.
- `OverlayContextMenu` still owns action rendering and action click behavior.
- `ZenModeOverlay` still owns elaboration request state and renders `ElaborationPreview`.

Use semantic priorities rather than reading z-index from CSS:

```text
LayerPriority.READER_OVERLAY
LayerPriority.CONTEXT_MENU
LayerPriority.DIALOG
```

The stack's top layer is the highest priority layer, with activation order as the tie-breaker. This keeps the model honest even if a lower-priority layer is registered later during a re-render.

## Phase 1: Add The Overlay Layer Stack

### 1. Create the provider and hook

**File**: `client/src/contexts/OverlayLayerContext.jsx`

Add an `OverlayLayerProvider` and `useOverlayLayer` hook.

The provider owns a mutable stack ref and one set of document-level listeners. The hook registers a layer while `active` is true and unregisters it on cleanup.

Pseudo shape:

```text
useOverlayLayer({
  active,
  priority,
  containerRef,
  initialFocusRef,
  onEscape,
  onOutsidePointerDown,
  focusMode,
  restoreFocus,
})
```

Where:

- `active`: whether this layer participates in the stack.
- `priority`: one of the semantic layer priorities.
- `containerRef`: DOM root used for outside-pointer and focus containment.
- `initialFocusRef`: preferred element to focus when the layer becomes active.
- `onEscape`: callback invoked only when this layer is topmost.
- `onOutsidePointerDown`: optional callback invoked only when this layer is topmost and the pointer target is outside `containerRef`.
- `focusMode`: `'none' | 'initial' | 'contain'`.
- `restoreFocus`: whether to restore the element that was focused before activation.

Do not use React state for the stack itself. Document listeners need immediate access to the current stack without reattaching on every registration.

### 2. Define stack behavior

**File**: `client/src/contexts/OverlayLayerContext.jsx`

The provider should install these listeners once:

- `keydown` in capture phase
- `pointerdown` in capture phase
- `focusin` in capture phase

Escape behavior:

```text
if key is not Escape, ignore
topLayer = getTopLayer()
if no topLayer or no topLayer.onEscape, ignore
prevent default
stop propagation
topLayer.onEscape()
```

Do not call `stopImmediatePropagation()`. There should be only one project-owned document Escape listener after this plan.

Pointer behavior:

```text
topLayer = getTopLayer()
if no topLayer.onOutsidePointerDown, ignore
if pointer target is inside topLayer.containerRef, ignore
topLayer.onOutsidePointerDown(event)
```

Focus behavior:

- On registration, remember `document.activeElement` if `restoreFocus` is true.
- For `focusMode: 'initial'`, focus `initialFocusRef` or the first focusable element once.
- For `focusMode: 'contain'`, focus initial/first on open, wrap Tab and Shift+Tab inside the container, and redirect `focusin` back into the top layer when focus moves outside.
- On unregister, restore the remembered element if it is still connected and focus restoration is enabled.

Use one local focusable-elements helper. Keep it small and boring:

```text
buttons, links, form fields, details summary, iframes, contenteditable, and non-negative tabindex
exclude disabled and aria-hidden elements
```

### 3. Mount the provider

**File**: `client/src/App.jsx`

Wrap the app content with `OverlayLayerProvider` near the existing root provider:

```text
InteractionProvider
  OverlayLayerProvider
    ToastContainer
    AppContent
```

Keep `ToastContainer` inside the provider only for tree consistency. Toasts must not call `useOverlayLayer`.

## Phase 2: Move BaseOverlay Onto The Stack

### 1. Register the reader overlay layer

**File**: `client/src/components/BaseOverlay.jsx`

Add refs for the portal root and the close button. Register `BaseOverlay` as a reader layer while mounted:

```text
useOverlayLayer({
  active: true,
  priority: LayerPriority.READER_OVERLAY,
  containerRef: overlayRootRef,
  initialFocusRef: closeButtonRef,
  onEscape: onClose,
  focusMode: 'contain',
  restoreFocus: true,
})
```

Because `BaseOverlay` is mounted only while open, `active: true` is enough.

### 2. Remove BaseOverlay's document Escape listener

**File**: `client/src/components/BaseOverlay.jsx`

Split the current effect:

- Keep body scroll lock.
- Delete the nested `handleEscape` function and `document.addEventListener('keydown', handleEscape)` calls.
- Delete the `event.defaultPrevented` guard and contract comment. The new contract is the stack.

The only document-level Escape listener after this plan should live in `OverlayLayerContext.jsx`.

### 3. Preserve existing portal click behavior

**File**: `client/src/components/BaseOverlay.jsx`

Keep the portal root click stop-propagation guard. Do not move the `data-overlay-content` marker, the scroll refs, the overlay menu render site, or gesture hooks in this phase.

## Phase 3: Move OverlayContextMenu Onto The Stack

### 1. Expose an outside-dismiss command from the menu hook

**File**: `client/src/hooks/useOverlayContextMenu.js`

Replace `useOverlayMenuDismissal` with a hook-owned outside-dismiss command.

The menu hook should keep the knowledge of whether outside dismissal should clear native selection, because that depends on `menuStateRef.current.source`.

Pseudo shape:

```text
handleOutsideDismiss():
  closeMenu({
    clearSelection: menuStateRef.current.source === MenuOpenSource.MOBILE_SELECTION
  })
```

Return that command from `useOverlayContextMenu` and include it in the `overlayMenu` contract built by `ZenModeOverlay`.

Keep `closeMenu()` as the command used by action clicks and Escape. It should still reset the mobile selection reducer before closing.

### 2. Delete the old dismissal effect

**File**: `client/src/hooks/useOverlayContextMenu.js`

Remove `useOverlayMenuDismissal` entirely, including:

- document `pointerdown` listener
- document `keydown` listener
- `stopImmediatePropagation()`

The hook still owns:

- menu state
- desktop right-click open
- mobile selection listeners and reducer decisions
- `enabled -> false` close behavior
- mobile reducer reset on close

### 3. Register the menu layer in the component

**File**: `client/src/components/OverlayContextMenu.jsx`

Move layer participation into the presentational component because it owns the actual menu DOM and the first-action ref.

Add a local root ref, merge it with the passed `menuRef`, and register:

```text
useOverlayLayer({
  active: isOpen,
  priority: LayerPriority.CONTEXT_MENU,
  containerRef: menuRootRef,
  initialFocusRef: firstActionRef,
  onEscape: onClose,
  onOutsidePointerDown: onOutsideDismiss,
  focusMode: 'contain',
  restoreFocus: true,
})
```

Remove the local effect that manually focuses `firstActionRef` on desktop. The stack hook owns focus entry now. If mobile browser behavior shows that auto-focus collapses native text selection before action click, use `focusMode: 'initial'` only on non-coarse pointers and `focusMode: 'none'` on coarse pointers. Make that decision in `OverlayContextMenu`; do not push pointer-media logic into the stack provider.

### 4. Preserve action-click semantics

**File**: `client/src/components/OverlayContextMenu.jsx`

Do not change `handleActionClick` semantics:

- prefer captured `selectedText`
- fall back to live `window.getSelection()`
- remove all ranges before closing
- call `onClose()`
- call `action.onSelect(text)`

This preserves the mobile selected-text race fix from `implementation/0-f-elaborate-action.md`.

## Phase 4: Move ElaborationPreview Onto The Stack

### 1. Register the dialog layer

**File**: `client/src/components/ElaborationPreview.jsx`

Add refs for the dialog panel and close button. Register the preview while `isOpen`:

```text
useOverlayLayer({
  active: isOpen,
  priority: LayerPriority.DIALOG,
  containerRef: dialogPanelRef,
  initialFocusRef: closeButtonRef,
  onEscape: onClose,
  focusMode: 'contain',
  restoreFocus: true,
})
```

Use the dialog panel as the focus container, not the full-screen backdrop. The backdrop button can remain a pointer close target, but keyboard focus should stay inside the actual dialog.

### 2. Remove the preview's document Escape listener

**File**: `client/src/components/ElaborationPreview.jsx`

Delete the `useEffect` that adds a capture-phase document `keydown` listener. The stack owns Escape now.

Keep:

- `role="dialog"`
- `aria-modal="true"`
- backdrop button close
- root click stop-propagation guard
- current z-index and animation

### 3. Preserve close/abort semantics

**Files**:

- `client/src/components/ElaborationPreview.jsx`
- `client/src/components/ZenModeOverlay.jsx`

Do not move `closeElaboration()` into the stack. The stack only calls `onClose`; Zen still owns aborting the in-flight elaboration request and resetting the elaboration state.

## Phase 5: Integrate Contracts Through Zen/BaseOverlay

### 1. Extend the overlay menu contract

**Files**:

- `client/src/components/ZenModeOverlay.jsx`
- `client/src/components/BaseOverlay.jsx`
- `client/src/components/OverlayContextMenu.jsx`

Add the outside-dismiss command to the `overlayMenu` contract:

```text
overlayMenu:
  isOpen
  anchor / position fields
  selectedText
  menuRef
  handleContextMenu
  closeMenu
  handleOutsideDismiss
  actions
```

`BaseOverlay` should pass `handleOutsideDismiss` through to `OverlayContextMenu`. It should not inspect menu source or selection state.

### 2. Keep Digest unchanged

**File**: `client/src/components/DigestOverlay.jsx`

No direct changes are expected. Digest gets reader-layer Escape/focus behavior automatically through `BaseOverlay`, but it still has no context menu until the digest elaboration plan lands.

If Digest needs a direct edit, it should only be due to a prop signature change in `BaseOverlay`, not menu wiring.

## Phase 6: Documentation And Research Trail

### 1. Update client architecture docs

**Files**:

- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`

Document:

- The overlay layer stack as the owner of topmost Escape, outside pointer dismissal, and focus containment.
- `BaseOverlay` registers as the reader layer.
- `OverlayContextMenu` registers as the context-menu layer.
- `ElaborationPreview` registers as the dialog layer.
- `event.defaultPrevented` and `stopImmediatePropagation()` are no longer part of the overlay/menu contract.
- Digest still does not consume the context menu, but it does participate in the reader layer through `BaseOverlay`.

In `STATE_MACHINES.md`, add the layer stack as a small cross-cutting machine or subsection near `BaseOverlay` and `Overlay Context Menu`. The important part is the event ownership rule:

```text
Escape -> OverlayLayerProvider -> top registered layer -> that layer's onEscape
```

### 2. Update the context-menu feature map

**File**: `thoughts/26-04-07-context-menu-research/0-b-feature-map.md`

Update the verified coupling points:

- Replace the current Escape arbitration bullet with the stack contract.
- Record that the menu and preview are registered layers above the reader overlay.
- Keep the `data-overlay-content` DOM marker as the mobile-selection scoping contract.

### 3. Add implementation log after landing

**File**: `thoughts/26-04-07-context-menu-research/implementation/5-add-real-layer-focus-stack-or-baseui-dialog-menu-primitive.md`

After implementation, add a concise note covering:

- why the local stack was chosen over BaseUI for this step
- which document listeners were removed
- what focus behavior was added to each layer
- what verification was run
- any browser/mobile focus nuance deliberately deferred

Do not manually update generated timestamp frontmatter.

## Acceptance Criteria

### Automated Verification

- [ ] `cd client && npm run build`
- [ ] `cd client && CI=true npm run lint`
- [ ] `rg -n "stopImmediatePropagation|event.defaultPrevented|defaultPrevented" client/src`
  - Expected: no source matches after docs/comments are updated away from the old contract.
- [ ] `rg -n "document.addEventListener\\('keydown'" client/src`
  - Expected: only `client/src/contexts/OverlayLayerContext.jsx`.
- [ ] `rg -n "useOverlayLayer" client/src/components client/src/contexts`
  - Expected: provider/hook plus `BaseOverlay.jsx`, `OverlayContextMenu.jsx`, and `ElaborationPreview.jsx`.
- [ ] `rg -n "useOverlayMenuDismissal" client/src`
  - Expected: no matches.
- [ ] `rg -n "OverlayLayerProvider" client/src/App.jsx client/src/contexts`
  - Expected: provider definition and app root usage.

Only fix build or lint failures introduced by this stack work.

### Manual Verification

Reader overlay:

1. Open a Zen summary overlay.
2. Press Escape.
3. Confirm the overlay closes and the article is marked read through the existing `summary.collapse()` path.
4. Reopen a Zen summary and Tab through the close button, source link, mark-done button, and any focusable content links. Confirm focus stays inside the reader shell.

Context menu:

1. Open a Zen summary overlay.
2. Right-click inside the prose.
3. Confirm the custom menu opens and the first action receives focus on desktop.
4. Press Escape once.
5. Confirm only the menu closes and the reader remains open.
6. Press Escape again.
7. Confirm the reader closes.
8. Reopen, select text on mobile or mobile emulation, let the menu open, tap outside it, and confirm the menu closes and native selection clears.

Elaboration preview:

1. Open a Zen summary overlay.
2. Select text, choose `Elaborate`, and wait for the preview.
3. Confirm focus moves to the preview close button.
4. Press Escape once.
5. Confirm only `ElaborationPreview` closes and the reader remains open.
6. Press Escape again.
7. Confirm the reader closes.
8. Start a slow elaboration if possible, close the preview/overlay, and confirm the existing abort/reset behavior still holds.

Digest regression:

1. Trigger a digest and confirm it opens normally.
2. Press Escape and confirm the digest closes through `digest.collapse(false)`.
3. Reopen the digest, use the check button, and confirm mark-removed lifecycle still works.
4. Confirm right-click inside digest prose still does not open the custom menu.

Portal and focus regression:

1. Click menu buttons and preview controls and confirm they do not bubble into the underlying `ArticleCard`.
2. With the menu or preview open, click/tap inside the active layer and confirm no outside-dismiss fires.
3. With the menu open, click outside the menu but inside the reader and confirm only the menu closes.
4. Confirm toasts still render visually above overlays but do not receive focus trapping or Escape ownership.

## Risk Notes

- Focus containment can disturb native mobile text selection if it eagerly focuses during a touch-selection flow. Keep coarse-pointer behavior conservative for `OverlayContextMenu`: preserve selected-text capture first, focus polish second.
- Do not replace the `zenLock` with the layer stack. The lock prevents multiple reader overlays from opening; the layer stack orders UI layers that are already open.
- Do not let the stack provider learn domain actions like "mark read" or "mark removed." It should only call registered callbacks.
- The provider's listeners must read refs, not stale React state. Registration/unregistration can update a mutable stack and a sequence counter.
- `stopPropagation()` is still allowed at portal roots to prevent React tree bubbling into `ArticleCard`. The thing being removed is `stopImmediatePropagation()` as cross-layer arbitration.
- If plan 4 has landed, preserve its `positionReference`/Floating UI work untouched. If plan 4 has not landed, leave raw `anchorX`/`anchorY` positioning untouched.

## References

- `thoughts/26-04-07-context-menu-research/impl-review/0-g-review-1.md`
- `thoughts/26-04-07-context-menu-research/plans/3-define-shared-overlay-menu-contract-then-wire-digest.plan.md`
- `thoughts/26-04-07-context-menu-research/plans/4-introduce-floating-ui-for-positioning-only.plan.md`
- `thoughts/26-04-07-context-menu-research/0-b-feature-map.md`
- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`
- `client/src/App.jsx`
- `client/src/components/BaseOverlay.jsx`
- `client/src/components/ZenModeOverlay.jsx`
- `client/src/components/DigestOverlay.jsx`
- `client/src/components/OverlayContextMenu.jsx`
- `client/src/components/ElaborationPreview.jsx`
- `client/src/components/ArticleCard.jsx`
- `client/src/components/ToastContainer.jsx`
- `client/src/hooks/useOverlayContextMenu.js`
- `client/src/reducers/mobileSelectionMenuReducer.js`
