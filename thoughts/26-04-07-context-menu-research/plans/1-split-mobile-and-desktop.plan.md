---
last_updated: 2026-04-23 20:31
originates_from: impl-review/review-1.md
status: implemented, 6c389c5
---

# Split Desktop and Mobile Overlay Menu Paths Implementation Plan

## Overview

Implement the first item from `impl-review/review-1.md`: split the desktop right-click path and the mobile text-selection path inside the overlay context menu. The goal is a behavior-preserving refactor that reduces timing/race complexity while keeping the public `useOverlayContextMenu` API stable for `ZenModeOverlay`.

This is intentionally a small first move. It should make later work easier, especially the mobile reducer and eventual Floating UI/BaseUI migration, without changing the visible product behavior in this pass.

## Current State Analysis

`client/src/hooks/useOverlayContextMenu.js` currently owns every path in one hook:

- Desktop right-click opens the menu from `handleContextMenu` at `useOverlayContextMenu.js:33`.
- Mobile selection is handled by document-level `selectionchange`, `touchstart`, and `touchend` listeners at `useOverlayContextMenu.js:47`.
- Close behavior for outside pointerdown and Escape is shared in a separate effect at `useOverlayContextMenu.js:121`.
- `openedBySelectionRef` at `useOverlayContextMenu.js:23` is the discriminator for whether closing should clear the browser selection.

The hook is consumed only by `ZenModeOverlay` today:

- `ZenModeOverlay.jsx:16` calls `useOverlayContextMenu(true)`.
- `ZenModeOverlay.jsx:133` threads `contextMenu.handleContextMenu` into `BaseOverlay`.
- `ZenModeOverlay.jsx:138` renders `OverlayContextMenu` with `contextMenu.isOpen`, anchor coordinates, `menuRef`, and `selectedText`.

The shared overlay contract still lives in `BaseOverlay`:

- `BaseOverlay.jsx:18` accepts `onContentContextMenu`.
- `BaseOverlay.jsx:52` respects `event.defaultPrevented` so Escape closes the menu before it closes the overlay.
- `BaseOverlay.jsx:114` attaches the context-menu handler to the scroll surface.
- `BaseOverlay.jsx:115` marks the selection scope with `data-overlay-content`.

`OverlayContextMenu` already depends on a captured `selectedText` when mobile selection collapses before click:

- `OverlayContextMenu.jsx:39` prefers the selected text captured at menu-open time.
- `OverlayContextMenu.jsx:41` clears the live browser selection when an action is clicked.

`DigestOverlay` composes `BaseOverlay` but does not compose the context menu. This plan must not accidentally wire Digest or change its behavior.

## Desired End State

`useOverlayContextMenu` remains the single exported hook and still returns the same UI-facing shape:

```js
{
  isOpen,
  anchorX,
  anchorY,
  selectedText,
  menuRef,
  handleContextMenu,
  closeMenu,
}
```

Internally, it delegates to three small owners:

1. `useDesktopContextMenu`: desktop right-click only.
2. `useMobileSelectionMenu`: mobile native text-selection only.
3. `useOverlayMenuDismissal`: close-on-outside and Escape only.

The visible behavior after implementation should be unchanged:

- Right-click in Zen prose opens the menu at the cursor.
- Mobile text selection in Zen prose opens the menu near the selection.
- Tapping Elaborate still receives the selected text.
- Outside pointerdown closes the menu.
- First Escape closes the menu only; second Escape closes the overlay.
- Digest overlay remains without a context menu.

## What We Are Not Doing

- No Floating UI or BaseUI migration.
- No reducer for mobile selection yet. That is the second recommended item.
- No Digest overlay context-menu wiring.
- No backend elaboration changes.
- No `BaseOverlay` contract relocation.
- No visual redesign of `OverlayContextMenu` or `ElaborationPreview`.
- No pull-to-close restoration. It stays disabled in `BaseOverlay` for native text selection.
- No broad debug-log cleanup unless a specific log line blocks verification.

## Implementation Approach

Keep the split inside `client/src/hooks/useOverlayContextMenu.js` for this first step. That gives the desired architectural separation without adding export churn or new folder structure. If the file becomes uncomfortable after the reducer step, move the private hooks into separate modules then.

Use an explicit menu open source in state, replacing `openedBySelectionRef` as the conceptual discriminator:

```js
const MenuOpenSource = Object.freeze({
  NONE: 'none',
  DESKTOP: 'desktop',
  MOBILE_SELECTION: 'mobile-selection',
})

const CLOSED_MENU_STATE = Object.freeze({
  isOpen: false,
  anchorX: 0,
  anchorY: 0,
  selectedText: '',
  source: MenuOpenSource.NONE,
})
```

Do not expose `source` from the public hook return. It is internal coordination state for close semantics.

Because document listeners need current state without constantly reattaching, mirror the current menu state into a ref:

```js
const menuStateRef = useRef(CLOSED_MENU_STATE)
useEffect(() => {
  menuStateRef.current = menuState
}, [menuState])
```

Then shared listeners can read `menuStateRef.current.source` instead of carrying a separate `openedBySelectionRef`.

## Phase 1: Split The Hook Internals

### 1. Add Internal Source-Aware Commands

**File**: `client/src/hooks/useOverlayContextMenu.js`

Replace the current direct `setMenuState(...)` calls and `openedBySelectionRef` writes with two internal commands:

```js
const openMenu = useCallback(({ source, anchorX, anchorY, selectedText = '' }) => {
  setMenuState({
    isOpen: true,
    anchorX,
    anchorY,
    selectedText,
    source,
  })
}, [])

const closeMenu = useCallback(({ clearSelection = false } = {}) => {
  if (clearSelection) window.getSelection()?.removeAllRanges()
  setMenuState(CLOSED_MENU_STATE)
}, [])
```

Notes:

- `closeMenu()` must keep working with no arguments because `ZenModeOverlay` passes it directly to `OverlayContextMenu`.
- `OverlayContextMenu` can keep clearing selection before it calls `onClose()`. This plan does not require changing action-click behavior.
- The source-aware close path is mainly for outside pointerdown, Escape, and mobile selection collapse.

### 2. Extract Desktop Right-Click Ownership

**File**: `client/src/hooks/useOverlayContextMenu.js`

Add a private hook in the same file:

```js
function useDesktopContextMenu({ enabled, openMenu }) {
  return useCallback((event) => {
    if (!enabled) return

    event.preventDefault()
    openMenu({
      source: MenuOpenSource.DESKTOP,
      anchorX: event.clientX,
      anchorY: event.clientY,
      selectedText: '',
    })
  }, [enabled, openMenu])
}
```

This hook should own only the `onContextMenu` path. It must not know about `selectionchange`, `touchstart`, `touchend`, Escape, outside pointerdown, or selection clearing.

Behavior to preserve:

- Desktop right-click should not call `window.getSelection().removeAllRanges()`.
- If the user right-clicks while text is selected, `OverlayContextMenu` can still fall back to the live selection at action click time.
- Non-enabled state is a no-op.

### 3. Extract Mobile Text Selection Ownership

**File**: `client/src/hooks/useOverlayContextMenu.js`

Add a private hook in the same file:

```js
function useMobileSelectionMenu({ enabled, openMenu, closeMenu, menuStateRef }) {
  useEffect(() => {
    if (!enabled) return
    if (!matchMedia('(pointer: coarse)').matches) return

    let touchActive = false

    function readOverlaySelection() {
      const selection = window.getSelection()
      const selectedText = selection?.toString().trim() ?? ''
      if (!selection || selection.isCollapsed || !selectedText) return null
      if (!selection.anchorNode?.parentElement?.closest('[data-overlay-content]')) return null

      const rect = selection.getRangeAt(0).getBoundingClientRect()
      return {
        anchorX: rect.left + rect.width / 2,
        anchorY: rect.bottom + 12,
        selectedText,
      }
    }

    function openFromSelection() {
      const selectionMenu = readOverlaySelection()
      if (!selectionMenu) return
      openMenu({
        source: MenuOpenSource.MOBILE_SELECTION,
        ...selectionMenu,
      })
    }

    function handleSelectionChange() {
      const selectionMenu = readOverlaySelection()
      const openedFromMobileSelection =
        menuStateRef.current.source === MenuOpenSource.MOBILE_SELECTION

      if (!selectionMenu) {
        if (openedFromMobileSelection && !touchActive) closeMenu()
        return
      }

      if (!touchActive) openFromSelection()
    }

    function handleTouchStart() {
      touchActive = true
    }

    function handleTouchEnd() {
      touchActive = false
      openFromSelection()
    }

    document.addEventListener('selectionchange', handleSelectionChange)
    document.addEventListener('touchstart', handleTouchStart, true)
    document.addEventListener('touchend', handleTouchEnd, true)

    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange)
      document.removeEventListener('touchstart', handleTouchStart, true)
      document.removeEventListener('touchend', handleTouchEnd, true)
    }
  }, [enabled, openMenu, closeMenu, menuStateRef])
}
```

Keep the same DOM contract:

- The mobile path must still ignore selections outside `[data-overlay-content]`.
- The menu should still open on finger lift (`touchend`) rather than mid-gesture.
- Clearing selection during a touch should not close the menu early, preserving the current ghost-click guard.

Avoid widening the scope:

- Do not add new mobile states like `idle`, `touching`, `selected`, or `closing` yet.
- Do not introduce a reducer in this pass.
- Do not change the positioning math yet.

### 4. Extract Shared Dismissal Ownership

**File**: `client/src/hooks/useOverlayContextMenu.js`

Move the current open-menu close effect into a private hook:

```js
function useOverlayMenuDismissal({ isOpen, menuRef, closeMenu, menuStateRef }) {
  useEffect(() => {
    if (!isOpen) return

    function handlePointerDown(event) {
      if (menuRef.current?.contains(event.target)) return

      closeMenu({
        clearSelection:
          menuStateRef.current.source === MenuOpenSource.MOBILE_SELECTION,
      })
    }

    function handleKeyDown(event) {
      if (event.key !== 'Escape') return

      event.preventDefault()
      event.stopPropagation()
      event.stopImmediatePropagation()
      closeMenu()
    }

    document.addEventListener('pointerdown', handlePointerDown, true)
    document.addEventListener('keydown', handleKeyDown, true)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown, true)
      document.removeEventListener('keydown', handleKeyDown, true)
    }
  }, [isOpen, menuRef, closeMenu, menuStateRef])
}
```

Behavior to preserve:

- Pointerdown inside the menu does nothing.
- Pointerdown outside the menu clears live selection only for mobile-selection-opened menus.
- Escape always closes the menu first and still prevents `BaseOverlay` from closing on that same keypress.

### 5. Recompose The Public Hook

**File**: `client/src/hooks/useOverlayContextMenu.js`

The exported hook should become the coordinator:

```js
export function useOverlayContextMenu(enabled = true) {
  const [menuState, setMenuState] = useState(CLOSED_MENU_STATE)
  const menuRef = useRef(null)
  const menuStateRef = useRef(menuState)

  useEffect(() => {
    menuStateRef.current = menuState
  }, [menuState])

  const openMenu = useCallback(...)
  const closeMenu = useCallback(...)

  const handleContextMenu = useDesktopContextMenu({ enabled, openMenu })
  useMobileSelectionMenu({ enabled, openMenu, closeMenu, menuStateRef })
  useOverlayMenuDismissal({
    isOpen: menuState.isOpen,
    menuRef,
    closeMenu,
    menuStateRef,
  })

  useEffect(() => {
    if (enabled) return
    closeMenu()
  }, [closeMenu, enabled])

  return {
    isOpen: menuState.isOpen,
    anchorX: menuState.anchorX,
    anchorY: menuState.anchorY,
    selectedText: menuState.selectedText,
    menuRef,
    handleContextMenu,
    closeMenu,
  }
}
```

The exported hook must still be called exactly the same way from `ZenModeOverlay`. No `ZenModeOverlay` code changes should be necessary unless the refactor exposes a stale callback issue.

### 6. Keep Consumers Stable

**Files**:

- `client/src/components/ZenModeOverlay.jsx`
- `client/src/components/OverlayContextMenu.jsx`
- `client/src/components/BaseOverlay.jsx`
- `client/src/components/DigestOverlay.jsx`

Expected changes:

- `ZenModeOverlay.jsx`: none.
- `OverlayContextMenu.jsx`: none, unless a type/shape mismatch requires using `selectedText ?? ''`.
- `BaseOverlay.jsx`: none.
- `DigestOverlay.jsx`: none.

If any of these files need behavioral edits, treat that as a sign the refactor is leaking. Stop and re-check the hook API before widening the diff.

### 7. Update Documentation After Verification

**Files**:

- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`
- `thoughts/26-04-07-context-menu-research/implementation/iteration-3.md` or equivalent implementation note, if continuing the existing research log pattern.

Documentation should say:

- The exported overlay context-menu primitive is still `useOverlayContextMenu`.
- Internally, desktop right-click and mobile selection are separate paths.
- The `BaseOverlay` contracts remain unchanged for now.
- Digest remains a planned consumer, not an implemented consumer.

Do not manually edit YAML frontmatter timestamps.

## Acceptance Criteria

### Automated Verification

- [ ] `cd client && npm run build`
- [ ] `cd client && CI=1 npm run lint`
- [ ] Search sanity: `rg -n "openedBySelectionRef|touchActive" client/src/hooks/useOverlayContextMenu.js`
  - `openedBySelectionRef` should be gone.
  - `touchActive` should only exist inside `useMobileSelectionMenu`.
- [ ] Search sanity: `rg -n "useOverlayContextMenu\\(" client/src`
  - The only current call site should remain `ZenModeOverlay`.

Only fix lint/build failures introduced by this refactor.

### Manual Verification

Desktop:

1. Open a Zen summary overlay.
2. Right-click in the prose body.
3. Confirm the custom menu opens at the cursor and the native browser context menu does not.
4. Press Escape once.
5. Confirm only the menu closes.
6. Press Escape again.
7. Confirm the overlay closes.
8. Reopen the overlay, select text with the mouse, right-click, choose Elaborate, and confirm the selected text reaches the preview.

Mobile or mobile emulation:

1. Open a Zen summary overlay.
2. Long-press still on text until native selection appears.
3. Confirm the custom menu opens near the selected text after finger lift.
4. Tap Elaborate.
5. Confirm the selection text is preserved and the elaboration preview opens.
6. Reopen and select text, then drag selection handles to extend the selection.
7. Confirm the menu remains tied to the selected text and does not close during the handle drag.
8. Tap outside the menu.
9. Confirm the menu closes and the native selection clears.

Regression checks:

1. Tap a normal article card with no text selected and confirm the summary open behavior still works.
2. Tap inside selected overlay prose and confirm the underlying `ArticleCard` does not receive a ghost click.
3. Use the bottom overscroll-up gesture and confirm mark-removed behavior is unchanged.
4. Open a digest overlay and confirm it still has no context menu behavior.
5. Confirm `ElaborationPreview` Escape/backdrop close still affects only the preview layer.

## Risk Notes

- Mobile selection is browser-owned state. The refactor should preserve the existing timing behavior before trying to improve it.
- `menuStateRef` is an implementation detail for document listeners. The canonical source should remain React state, not a pile of independent refs.
- Do not move the `data-overlay-content` contract yet. The third recommended review item owns that.
- Do not change `OverlayContextMenu` positioning yet. Floating UI is the fourth recommended item.
- Keep the diff boring. The purpose of this step is to untangle, not to add capability.

## References

- `thoughts/26-04-07-context-menu-research/impl-review/review-1.md`
- `thoughts/26-04-07-context-menu-research/implementation/iteration-1.md`
- `thoughts/26-04-07-context-menu-research/implementation/iteration-2.md`
- `client/src/hooks/useOverlayContextMenu.js`
- `client/src/components/OverlayContextMenu.jsx`
- `client/src/components/BaseOverlay.jsx`
- `client/src/components/ZenModeOverlay.jsx`
- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`
