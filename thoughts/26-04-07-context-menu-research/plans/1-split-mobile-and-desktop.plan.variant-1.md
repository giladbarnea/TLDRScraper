---
last_updated: 2026-04-21 21:03
originates_from: impl-review/review-1.md
---

# Plan: Split Desktop and Mobile Context-Menu Paths

## Goal

Decompose the monolithic `useOverlayContextMenu` hook into two narrow, self-contained hooks — `useDesktopContextMenu` and `useMobileSelectionMenu` — while keeping `useOverlayContextMenu` as the stable public API. This directly addresses Review-1 point 4 ("Split desktop and mobile") and shrinks the surface area for the follow-up reducer refactor (Recommended order step 2).

## Scope

**In scope**
- `client/src/hooks/useOverlayContextMenu.js` — rewrite to a thin router.
- `client/src/hooks/useDesktopContextMenu.js` — new.
- `client/src/hooks/useMobileSelectionMenu.js` — new.
- `client/src/components/OverlayContextMenu.jsx` — remove the live-selection fallback now that both paths capture `selectedText` at open time.

**Out of scope**
- No changes to `BaseOverlay.jsx` (the `data-overlay-content` and `defaultPrevented` contracts stay intact).
- No changes to `ZenModeOverlay.jsx` (it continues to call `useOverlayContextMenu(true)` and pass `handleContextMenu` into `BaseOverlay`).
- No reducer refactor yet (that is step 2 in the recommended order).
- No Floating UI or focus-stack changes yet (steps 4 and 5).

## Why this is the right first move

- High impact: it untangles two genuinely different interaction models (right-click vs. text-selection-then-touch) that currently share one state object and one set of refs.
- Low product risk: the external contract is unchanged; `ZenModeOverlay` and `BaseOverlay` require zero changes.
- Paves the way: a later mobile reducer only needs to touch `useMobileSelectionMenu.js`, and a Floating UI positioning adapter can wrap both sub-hooks through the same outer API.

## New file: `client/src/hooks/useDesktopContextMenu.js`

Owns desktop right-click → menu. No touch or selection concerns.

```js
import { useCallback, useEffect, useRef, useState } from 'react'

const CLOSED = Object.freeze({ isOpen: false, anchorX: 0, anchorY: 0, selectedText: '' })

export function useDesktopContextMenu(enabled) {
  const [state, setState] = useState(CLOSED)
  const menuRef = useRef(null)

  const closeMenu = useCallback(() => setState(CLOSED), [])

  const handleContextMenu = useCallback((event) => {
    if (!enabled) return
    event.preventDefault()
    const selectedText = window.getSelection()?.toString() || ''
    setState({
      isOpen: true,
      anchorX: event.clientX,
      anchorY: event.clientY,
      selectedText,
    })
  }, [enabled])

  // Close when the owning overlay disables the hook (e.g. overlay unmounts).
  useEffect(() => {
    if (!enabled) closeMenu()
  }, [enabled, closeMenu])

  // Dismiss lifecycle: outside click and Escape.
  useEffect(() => {
    if (!state.isOpen) return

    function onPointerDown(event) {
      if (menuRef.current?.contains(event.target)) return
      closeMenu()
    }

    function onKeyDown(event) {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopPropagation()
      event.stopImmediatePropagation()
      closeMenu()
    }

    document.addEventListener('pointerdown', onPointerDown, true)
    document.addEventListener('keydown', onKeyDown, true)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown, true)
      document.removeEventListener('keydown', onKeyDown, true)
    }
  }, [state.isOpen, closeMenu])

  return { ...state, menuRef, handleContextMenu, closeMenu }
}
```

Key decisions:
- Captures `selectedText` at open time so `OverlayContextMenu` never needs a live-selection fallback. This keeps the desktop path consistent with the mobile fix from iteration 2.
- Keeps the capture-phase Escape suppression exactly as today; `BaseOverlay` still guards with `defaultPrevented`.

## New file: `client/src/hooks/useMobileSelectionMenu.js`

Owns mobile text-selection → menu. No right-click concerns.

```js
import { useCallback, useEffect, useRef, useState } from 'react'

const CLOSED = Object.freeze({ isOpen: false, anchorX: 0, anchorY: 0, selectedText: '' })

export function useMobileSelectionMenu(enabled) {
  const [state, setState] = useState(CLOSED)
  const menuRef = useRef(null)
  const openedBySelectionRef = useRef(false)

  const closeMenu = useCallback(() => {
    openedBySelectionRef.current = false
    setState(CLOSED)
  }, [])

  const openMenuFromSelection = useCallback(() => {
    const sel = window.getSelection()
    const text = sel?.toString().trim() ?? ''
    if (!sel || sel.isCollapsed || !text) return
    if (!sel.anchorNode?.parentElement?.closest('[data-overlay-content]')) return

    const rect = sel.getRangeAt(0).getBoundingClientRect()
    openedBySelectionRef.current = true
    setState({
      isOpen: true,
      anchorX: rect.left + rect.width / 2,
      anchorY: rect.bottom + 12,
      selectedText: text,
    })
  }, [])

  // Selection and touch listeners.
  useEffect(() => {
    if (!enabled) return

    let touchActive = false

    function onSelectionChange() {
      const sel = window.getSelection()
      const text = sel?.toString().trim() ?? ''
      if (!sel || sel.isCollapsed || !text) {
        if (openedBySelectionRef.current && !touchActive) closeMenu()
        return
      }
      if (!touchActive) openMenuFromSelection()
    }

    function onTouchStart() { touchActive = true }
    function onTouchEnd() {
      touchActive = false
      openMenuFromSelection()
    }

    document.addEventListener('selectionchange', onSelectionChange)
    document.addEventListener('touchstart', onTouchStart, true)
    document.addEventListener('touchend', onTouchEnd, true)
    return () => {
      document.removeEventListener('selectionchange', onSelectionChange)
      document.removeEventListener('touchstart', onTouchStart, true)
      document.removeEventListener('touchend', onTouchEnd, true)
    }
  }, [enabled, closeMenu, openMenuFromSelection])

  // Close when disabled.
  useEffect(() => {
    if (!enabled) closeMenu()
  }, [enabled, closeMenu])

  // Dismiss lifecycle: outside click (clears selection if opened by selection) and Escape.
  useEffect(() => {
    if (!state.isOpen) return

    function onPointerDown(event) {
      if (menuRef.current?.contains(event.target)) return
      if (openedBySelectionRef.current) window.getSelection()?.removeAllRanges()
      closeMenu()
    }

    function onKeyDown(event) {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopPropagation()
      event.stopImmediatePropagation()
      closeMenu()
    }

    document.addEventListener('pointerdown', onPointerDown, true)
    document.addEventListener('keydown', onKeyDown, true)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown, true)
      document.removeEventListener('keydown', onKeyDown, true)
    }
  }, [state.isOpen, closeMenu])

  return { ...state, menuRef, handleContextMenu: null, closeMenu }
}
```

Key decisions:
- The `touchActive` flag stays a local `let` inside the effect (not state or ref) because it is purely an event-boundary guard, not UI state.
- `openedBySelectionRef` stays a ref because it is read synchronously inside event handlers and must not trigger re-renders.
- Returns `handleContextMenu: null` because mobile has no right-click path; `BaseOverlay`'s `onContextMenu={null}` is harmless.

## Rewrite: `client/src/hooks/useOverlayContextMenu.js`

Becomes a reactive router that picks the correct sub-hook based on pointer type.

```js
import { useEffect, useState } from 'react'
import { useDesktopContextMenu } from './useDesktopContextMenu'
import { useMobileSelectionMenu } from './useMobileSelectionMenu'

export function useOverlayContextMenu(enabled = true) {
  const [isCoarse, setIsCoarse] = useState(() => matchMedia('(pointer: coarse)').matches)

  useEffect(() => {
    const mql = matchMedia('(pointer: coarse)')
    const onChange = (e) => setIsCoarse(e.matches)
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [])

  const desktop = useDesktopContextMenu(enabled && !isCoarse)
  const mobile = useMobileSelectionMenu(enabled && isCoarse)

  const active = isCoarse ? mobile : desktop

  console.log('[ctxmenu] render — enabled:', enabled, '| isCoarse:', isCoarse, '| isOpen:', active.isOpen)

  return active
}
```

Key decisions:
- Both sub-hooks are called unconditionally (required by Rules of Hooks). Each receives its own `enabled` boolean and internally no-ops when disabled.
- `matchMedia` is read into state with a change listener so devtools mobile emulation toggles are handled without a reload.
- Preserve the existing debug log for continuity.
- The CONTRACT comment block that lives in this file today (documenting `data-overlay-content` and `defaultPrevented`) stays here, because it describes the public contract between `useOverlayContextMenu` and its consumers.

## Minor update: `client/src/components/OverlayContextMenu.jsx`

Because both sub-hooks now capture `selectedText` at menu-open time, the live-selection fallback is dead code.

In `handleActionClick`:

```js
// Before
const text = selectedText || window.getSelection()?.toString() || ''
console.log('[ctxmenu] action click — key:', action.key, '| text:', text.slice(0, 40), '| live:', window.getSelection()?.toString()?.slice(0, 40))

// After
const text = selectedText || ''
console.log('[ctxmenu] action click — key:', action.key, '| text:', text.slice(0, 40))
```

The `window.getSelection()?.removeAllRanges()` call after `onClose()` stays; clearing the selection after the user taps an action is still correct UX.

## Verification checklist

1. **Build**
   ```bash
   cd client && npm run build
   ```
   Must pass with zero new warnings.

2. **Desktop manual**
   - Right-click inside Zen overlay prose → custom menu appears at cursor.
   - Select text, then right-click → menu opens and "Elaborate" uses the selected text.
   - Escape with menu open → menu closes only; a second Escape closes the overlay.
   - Click outside menu → menu closes.

3. **Mobile manual (iOS Safari / Android Chrome)**
   - Long-press to select text inside Zen overlay → selection handles appear.
   - Lift finger → menu opens below the selection.
   - Tap "Elaborate" → selected text is sent to `/api/elaborate` (check Network tab).
   - Tap outside menu before choosing an action → menu closes and selection is cleared.
   - Escape (where available) closes menu only.

4. **DigestOverlay regression**
   - Open Digest overlay.
   - Confirm pull-to-close and overscroll-up gestures still behave.
   - Confirm no context menu appears on right-click or text selection (Digest does not compose `useOverlayContextMenu`).

## Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Hook-switching on `matchMedia` change causes stale state from the previously-active sub-hook | Acceptable: the inactive sub-hook’s state is simply ignored. Its listeners are disabled via its own `enabled` effect, so it cannot open spontaneously. |
| `handleContextMenu: null` on mobile causes React warning | `onContextMenu={null}` is valid React and attaches no listener. |
| `useDesktopContextMenu` and `useMobileSelectionMenu` duplicate the dismiss effect (pointerdown + Escape) | Acceptable for now. The duplicated block is ~15 lines. If a third menu variant appears, extract a shared `useMenuDismiss` hook. Do not pre-emptively abstract. |

## What this paves

- **Step 2 (mobile reducer)**: `useMobileSelectionMenu.js` is now isolated; replacing `openedBySelectionRef` + `touchActive` with an explicit state machine only touches one file.
- **Step 4 (Floating UI positioning)**: Positioning logic can be injected into both sub-hooks through a shared helper without touching `ZenModeOverlay` or `BaseOverlay`.
- **Step 3 (shared overlay-menu contract)**: Once `DigestOverlay` adopts the menu, it can call `useOverlayContextMenu` exactly as `ZenModeOverlay` does today.
