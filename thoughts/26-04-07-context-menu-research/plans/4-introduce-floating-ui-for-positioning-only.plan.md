---
originates_from: impl-review/0-g-review-1.md
last_updated: 2026-04-27 21:21, b387f55
---

# Introduce Floating UI For Positioning Only Implementation Plan

## Overview

Implement the fourth item from `impl-review/0-g-review-1.md`: replace the hand-written overlay context-menu viewport math with Floating UI positioning, without changing the menu's actions, open/close lifecycle, Escape arbitration, mobile selection reducer, shared overlay contract, or elaboration behavior.

This is intentionally the smallest useful platform adoption slice. It should remove `clampMenuPosition()` from `OverlayContextMenu.jsx`, let a battle-tested positioning primitive handle viewport edges, and leave the still-custom interaction model intact until the later focus-stack/BaseUI work.

## Current State Analysis

The current positioning system is local and hand-rolled:

- `client/src/components/OverlayContextMenu.jsx:4-16` declares fixed menu dimensions and clamps raw `anchorX` / `anchorY` against `window.innerWidth` and `window.innerHeight`.
- `client/src/components/OverlayContextMenu.jsx:31` computes the clamped position during render, and `client/src/components/OverlayContextMenu.jsx:54` writes `left` / `top` directly.
- `client/src/hooks/useOverlayContextMenu.js:99-102` opens desktop menus from the right-click `clientX` / `clientY`.
- `client/src/hooks/useOverlayContextMenu.js:132-134` opens mobile-selection menus from the selection bounding rect's horizontal center and `rect.bottom + 12`.
- `client/STATE_MACHINES.md:911-914` documents a current nuance: mobile selection pre-centers `anchorX`, but `clampMenuPosition()` still left-aligns the menu at that point, so the menu is not truly centered under the selection.
- `client/package.json:12-20` does not currently include any Floating UI package.

The interaction graph around this component is already separated:

- `useOverlayContextMenu` owns menu state, desktop right-click, mobile selection, outside pointerdown, and Escape dismissal.
- `OverlayContextMenu` owns only rendering, action click handling, focus-on-open for desktop, and positioning.
- `BaseOverlay` owns the scroll surface and the `data-overlay-content` contract.
- `ZenModeOverlay` currently renders the menu directly; `plans/3-define-shared-overlay-menu-contract-then-wire-digest.plan.md` intends to move the render site into `BaseOverlay` and wire `DigestOverlay`.

This plan is compatible with either the current render site or the planned shared render site. It should land after plan 3 if plan 3 is in progress; if it lands first, it must still not move the render site or wire Digest.

## Desired End State

After implementation:

- `@floating-ui/react-dom` is installed because this slice needs positioning only, not Floating UI's interaction hooks.
- `OverlayContextMenu` uses `useFloating()` and middleware for its coordinates instead of `clampMenuPosition()`.
- The menu remains a manually rendered React portal with the existing root click-propagation guard.
- Desktop right-click still opens at the cursor.
- Mobile text selection opens below the selected range and is centered by positioning semantics, not by subtracting hard-coded menu width in project code.
- Edge behavior is handled by middleware: the menu stays in the viewport near the top, bottom, left, and right edges.
- The existing action model remains unchanged: `OverlayContextMenu.handleActionClick()` still uses captured `selectedText`, clears the native selection, closes the menu, and calls `action.onSelect(text)`.

## Key Discoveries

- Floating UI's React docs recommend `@floating-ui/react-dom` when only positioning is needed; the larger `@floating-ui/react` package is for interaction hooks as well.
- `useFloating()` supports `strategy: 'fixed'`, which matches the current portaled `fixed` menu and avoids overlay scroll-container clipping.
- `useFloating()` supports `transform: false`; this matters because `animate-overlay-menu-enter` in `client/src/index.css:100-112` already uses CSS transforms.
- Floating UI virtual elements are designed for context menus and range selections. A cursor can be modeled as a zero-size point, while a text selection can be modeled from a copied `Range.getBoundingClientRect()` plus copied client rects.
- The `inline()` middleware is specifically intended for inline references and range selections that span multiple lines. It belongs in this positioning slice because it affects placement only, not interaction behavior.

## What We Are Not Doing

- No `@floating-ui/react` interaction hooks such as `useDismiss`, `useRole`, `useClick`, or `FloatingFocusManager`.
- No BaseUI migration.
- No layer/focus stack work.
- No Escape ownership rewrite; `event.defaultPrevented` / capture-phase arbitration remains as-is.
- No Digest wiring or shared overlay-menu contract work. That belongs to plan 3.
- No mobile selection reducer changes.
- No pull-to-close restoration.
- No backend elaboration changes.
- No visual redesign of `OverlayContextMenu` or `ElaborationPreview`.
- No cleanup of `[ctxmenu]` debug logging unless the implementation directly touches a line and removal is necessary for verification clarity.

## Implementation Approach

Use Floating UI as a positioning adapter only. Keep `useOverlayContextMenu` as the source of "where the menu should attach," and keep `OverlayContextMenu` as the source of "how the floating menu is positioned and rendered."

The project should stop passing only raw `anchorX` / `anchorY` as the full positioning model. Raw points are enough for desktop right-click, but not enough for text selections. The hook should instead produce a small positioning reference snapshot:

```text
positionReference:
  kind: 'point' | 'range'
  x, y                       # retained for traceability/debugging
  boundingRect               # plain viewport-relative rect snapshot
  clientRects                # range-only, copied at selection-read time
  placement                  # 'bottom-start' for cursor, 'bottom' for selection
  offsetPx                   # 0 for cursor, 12 for selection
```

`OverlayContextMenu` then converts that plain snapshot into a Floating UI virtual element at render time. Do not store live `Range` objects in React state; copy their rects while the selection is still valid.

## Phase 1: Add The Positioning Dependency

### 1. Install the positioning-only package

**Files**:

- `client/package.json`
- `client/package-lock.json`

Add `@floating-ui/react-dom` as a client dependency using npm from the `client/` directory.

Use the positioning-only package because this plan does not need Floating UI interaction primitives. The expected import surface is:

```js
autoUpdate
flip
inline
offset
shift
useFloating
```

Do not install globally. Do not add `@floating-ui/react` unless the implementation discovers that `@floating-ui/react-dom` cannot supply the required positioning API.

## Phase 2: Preserve Better Anchor Data In The Hook

### 1. Replace raw-coordinate-only state with a positioning snapshot

**File**: `client/src/hooks/useOverlayContextMenu.js`

Extend the closed/open menu state so each open menu has an explicit `positionReference`. Keep `anchorX` and `anchorY` only if useful for existing docs or transitional call sites, but do not make `OverlayContextMenu` depend on them after this plan.

The default closed state should have no usable positioning reference. An open menu must always have one.

Pseudo shape:

```js
CLOSED_MENU_STATE:
  isOpen: false
  selectedText: ''
  source: MenuOpenSource.NONE
  positionReference: null
```

`openMenu()` should require a complete `positionReference` from each trigger path. If a future caller opens the menu without one, that is a programming error worth surfacing during development rather than silently falling back to `(0, 0)`.

### 2. Build a point reference for desktop right-click

**File**: `client/src/hooks/useOverlayContextMenu.js`

In `useDesktopContextMenu`, create a point positioning snapshot from the right-click event:

```js
positionReference:
  kind: 'point'
  x: event.clientX
  y: event.clientY
  boundingRect: zero-size rect at clientX/clientY
  clientRects: []
  placement: 'bottom-start'
  offsetPx: 0
```

This preserves the current behavior where the menu's top-left edge starts at the cursor, subject to viewport collision handling.

### 3. Build a range reference for mobile selection

**File**: `client/src/hooks/useOverlayContextMenu.js`

In `readOverlaySelection()`, keep the existing scope check against `[data-overlay-content]`, then copy the selected range geometry:

```js
range = selection.getRangeAt(0)
boundingRect = copyDomRect(range.getBoundingClientRect())
clientRects = copy every rect from range.getClientRects()
```

Return a selection object that includes:

```js
positionReference:
  kind: 'range'
  x: boundingRect.left + boundingRect.width / 2
  y: boundingRect.bottom
  boundingRect
  clientRects
  placement: 'bottom'
  offsetPx: 12
```

This preserves the old vertical gap (`rect.bottom + 12`) through Floating UI's `offset(12)` middleware, and fixes the documented center-alignment nuance by using `placement: 'bottom'` against a range reference rather than left-aligning at a pre-centered coordinate.

If `getClientRects()` returns no usable rects, fail clearly in the selection reader by returning `null`; do not invent a secondary fallback path.

### 4. Keep reducer decisions unchanged

**Files**:

- `client/src/hooks/useOverlayContextMenu.js`
- `client/src/reducers/mobileSelectionMenuReducer.js`

The mobile reducer should continue to receive and return the selection object. The only change is that the selection object now carries a richer `positionReference` snapshot alongside `anchorX`, `anchorY`, and `selectedText`.

Do not change reducer states or transitions in this plan.

## Phase 3: Replace `clampMenuPosition()` With Floating UI

### 1. Remove custom viewport math

**File**: `client/src/components/OverlayContextMenu.jsx`

Delete:

- `MENU_WIDTH_PX`
- `MENU_VERTICAL_PADDING_PX`
- `MENU_ITEM_HEIGHT_PX`
- `clampMenuPosition(anchorX, anchorY, actionCount)`
- render-time `const position = clampMenuPosition(...)`

Keep:

- `MENU_EDGE_GAP_PX`
- fixed visual width (`w-[184px]`)
- action rendering
- desktop autofocus behavior
- root `onClick={(e) => e.stopPropagation()}`
- root `onContextMenu={(event) => event.preventDefault()}`

### 2. Create virtual references from snapshots

**File**: `client/src/components/OverlayContextMenu.jsx`

Add a tiny local conversion from the plain `positionReference` snapshot to a Floating UI virtual element:

```js
createVirtualReference(positionReference):
  getBoundingClientRect -> positionReference.boundingRect
  getClientRects -> positionReference.clientRects
```

For point references, `clientRects` can be an empty list and the bounding rect is the zero-size cursor rect. For range references, both the bounding rect and client rects are copied from the original selection range.

### 3. Use `useFloating()` for coordinates

**File**: `client/src/components/OverlayContextMenu.jsx`

Use Floating UI with these semantics:

```js
useFloating:
  open: isOpen
  placement: positionReference.placement
  strategy: 'fixed'
  transform: false
  whileElementsMounted: autoUpdate
  middleware:
    inline() only for range references
    offset(positionReference.offsetPx)
    flip()
    shift({ padding: MENU_EDGE_GAP_PX })
```

Notes:

- `strategy: 'fixed'` matches the existing portaled `fixed` menu.
- `transform: false` avoids colliding with `animate-overlay-menu-enter`, which uses `transform`.
- `inline()` should run before `flip()` and `shift()` for range references.
- `flip()` and `shift()` replace the project's viewport clamp.

### 4. Merge the Floating UI ref with the existing dismissal ref

**File**: `client/src/components/OverlayContextMenu.jsx`

The `menuRef` passed from `useOverlayContextMenu` is still required by `useOverlayMenuDismissal()` for outside-pointer detection. Floating UI also needs a floating ref.

Use one callback ref that writes to both owners:

```js
setMenuNode(node):
  menuRef.current = node
  floatingRefs.setFloating(node)
```

Do not replace `menuRef` with a private local ref; that would break outside pointerdown semantics.

### 5. Apply Floating UI styles without changing visual styling

**File**: `client/src/components/OverlayContextMenu.jsx`

Replace the manual `style={{ left, top }}` with Floating UI's positioning styles. Keep the menu's visual Tailwind classes as they are.

Use `isPositioned` to avoid a one-frame flash at `(0, 0)` while Floating UI computes the initial coordinates:

```js
style:
  ...floatingStyles
  visibility: isPositioned ? 'visible' : 'hidden'
```

The menu remains conditionally rendered only when `isOpen` is true.

## Phase 4: Keep Integration Boundaries Stable

### 1. Update the current menu call site

**File**: `client/src/components/ZenModeOverlay.jsx`

If plan 3 has not landed yet, pass `contextMenu.positionReference` into `OverlayContextMenu` from `ZenModeOverlay` and remove the old `anchorX` / `anchorY` props from that call.

Do not change:

- the `Elaborate` action
- `runElaboration()`
- `ElaborationPreview`
- `BaseOverlay` props
- `onContentContextMenu`

### 2. Update the shared render site if plan 3 has landed

**File**: `client/src/components/BaseOverlay.jsx`

If plan 3 has landed and `BaseOverlay` renders `OverlayContextMenu`, thread the new `positionReference` through the explicit `overlayMenu` contract instead.

Do not use this plan to introduce the `overlayMenu` contract. If that contract is absent, leave `BaseOverlay` alone.

### 3. Keep Digest behavior scoped to the already-landed state

**File**: `client/src/components/DigestOverlay.jsx`

If plan 3 has not landed, Digest remains untouched and without a context menu.

If plan 3 has landed, Digest automatically gets the same Floating UI positioning because it uses the same `OverlayContextMenu` render path. Do not add Digest-specific positioning branches.

## Phase 5: Documentation And Research Trail

### 1. Update client docs

**Files**:

- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`

Update the overlay context-menu positioning description:

- replace `clampMenuPosition()` with Floating UI positioning
- describe point references for desktop context menu opens
- describe range references for mobile/native selection opens
- note that `flip()` / `shift()` handle viewport collision
- remove the documented left-aligned-at-selection-center nuance

Keep the docs aligned with whether plan 3 has landed. If Digest is still not wired, do not claim it is wired.

### 2. Add implementation log

**File**: `thoughts/26-04-07-context-menu-research/implementation/4-introduce-floating-ui-for-positioning-only.md`

After implementation, add a concise note covering:

- dependency added
- custom viewport math removed
- virtual reference shape chosen
- verification run
- any visual differences observed at viewport edges

Do not manually add or update timestamp frontmatter.

## Acceptance Criteria

### Automated Verification

- [ ] `cd client && npm run build`
- [ ] `cd client && CI=1 npm run lint`
- [ ] `cd client && npm ls @floating-ui/react-dom`
- [ ] `rg -n "clampMenuPosition|MENU_WIDTH_PX|MENU_ITEM_HEIGHT_PX|MENU_VERTICAL_PADDING_PX" client/src`
  - Expected: no matches.
- [ ] `rg -n "@floating-ui/react-dom|useFloating|autoUpdate|shift\\(|flip\\(|inline\\(" client/src/components/OverlayContextMenu.jsx`
  - Expected: imports and use in `OverlayContextMenu.jsx`.
- [ ] `rg -n "anchorX=|anchorY=" client/src/components`
  - Expected: no `OverlayContextMenu` call site still passes raw anchor coordinates.

Only fix build or lint failures introduced by this work.

### Manual Verification

Desktop:

1. Open a Zen summary overlay.
2. Right-click near the middle of the prose and confirm the menu appears at the cursor.
3. Right-click near the right edge and confirm the menu shifts into the viewport.
4. Right-click near the bottom edge and confirm the menu flips or shifts into view rather than clipping.
5. Press Escape once and confirm only the menu closes.
6. Press Escape again and confirm the overlay closes.
7. Select text with the mouse, right-click, choose `Elaborate`, and confirm the selected text reaches `ElaborationPreview`.

Mobile or mobile emulation:

1. Open a Zen summary overlay.
2. Long-press text until native selection appears, then lift.
3. Confirm the menu opens below and centered relative to the selected range.
4. Select text spanning multiple lines and confirm the menu stays visually attached to the selected line/range rather than the whole bounding box feeling detached.
5. Select text near the bottom of the viewport and confirm the menu remains visible.
6. Tap `Elaborate` and confirm captured selected text is preserved.
7. Tap outside the menu and confirm the menu closes and native selection clears.

Regression checks:

1. Confirm menu clicks still do not bubble to `ArticleCard`.
2. Confirm `ElaborationPreview` Escape and backdrop behavior is unchanged.
3. Confirm bottom overscroll-up still marks the article or digest consumed as before.
4. If plan 3 has landed, repeat desktop and mobile menu checks inside `DigestOverlay` with its digest-safe actions.
5. Confirm the menu entrance animation still runs correctly after `transform: false` is set in Floating UI.

## Risk Notes

- Floating UI computes the initial position asynchronously. Use `open` + `isPositioned` to prevent a visible flash before coordinates settle.
- The existing animation uses CSS transforms. Do not let Floating UI also position via transforms on the same element.
- The mobile selection path must copy rect data immediately. Do not store a live `Range` in React state; native selection may collapse before click handlers run.
- The richer `positionReference` object is positioning state, not a new interaction state machine. Keep transition decisions in `mobileSelectionMenuReducer.js`.
- Do not widen this into focus management. That is recommended item 5 and should remain a separate, more deliberate change.

## References

- `thoughts/26-04-07-context-menu-research/impl-review/0-g-review-1.md`
- `thoughts/26-04-07-context-menu-research/plans/1-split-mobile-and-desktop.plan.md`
- `thoughts/26-04-07-context-menu-research/plans/2-make-mobile-selection-state-explicit.plan.md`
- `thoughts/26-04-07-context-menu-research/plans/3-define-shared-overlay-menu-contract-then-wire-digest.plan.md`
- `client/src/components/OverlayContextMenu.jsx`
- `client/src/hooks/useOverlayContextMenu.js`
- `client/src/components/BaseOverlay.jsx`
- `client/src/components/ZenModeOverlay.jsx`
- `client/src/components/DigestOverlay.jsx`
- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`
- Floating UI React docs: https://floating-ui.com/docs/react
- Floating UI `useFloating` docs: https://floating-ui.com/docs/usefloating
- Floating UI virtual elements docs: https://floating-ui.com/docs/virtual-elements
- Floating UI `inline` middleware docs: https://floating-ui.com/docs/inline
