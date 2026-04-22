---
last_updated: 2026-04-22 09:31
originates_from: impl-review/review-1.md
---

# Plan: Split Desktop and Mobile Context-Menu Paths

## Goal

Decompose the `useOverlayContextMenu` hook into two separate hooks — `useDesktopContextMenu` and `useMobileSelectionMenu` — while keeping `useOverlayContextMenu` as the public API. This addresses Review-1 point 4 ("Split desktop and mobile") and isolates the scope for the follow-up reducer refactor (Recommended order step 2).

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

## Rationale

- Separates the two interaction models (right-click vs. text-selection-then-touch) that currently share one state object and one set of refs.
- The external contract is unchanged; `ZenModeOverlay` and `BaseOverlay` require no changes.
- A future mobile reducer will only need to modify `useMobileSelectionMenu.js`, and a Floating UI positioning adapter can wrap both sub-hooks via the outer API.

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

Implementation details:
- Captures `selectedText` at open time, removing the need for a live-selection fallback in `OverlayContextMenu`. This aligns the desktop path with the mobile implementation from iteration 2.
- Keeps the capture-phase Escape suppression as is; `BaseOverlay` continues to check `defaultPrevented`.

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

Implementation details:
- The `touchActive` flag is maintained as a local `let` inside the effect, functioning as an event-boundary guard rather than UI state.
- `openedBySelectionRef` remains a ref to allow synchronous reading inside event handlers without triggering re-renders.
- Returns `handleContextMenu: null` as mobile has no right-click path; passing `onContextMenu={null}` to `BaseOverlay` is valid.

## Rewrite: `client/src/hooks/useOverlayContextMenu.js`

Acts as a router that selects the active sub-hook based on pointer type.

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

Implementation details:
- Both sub-hooks are called unconditionally to comply with the Rules of Hooks. Each receives its own `enabled` boolean and no-ops internally when disabled.
- `matchMedia` is read into state with a change listener to support devtools mobile emulation toggles without reloading.
- Preserves the existing debug log.
- Retains the CONTRACT comment block in this file, as it documents the public contract (`data-overlay-content` and `defaultPrevented`) for consumers of `useOverlayContextMenu`.

## Minor update: `client/src/components/OverlayContextMenu.jsx`

Both sub-hooks capture `selectedText` at menu-open time, making the live-selection fallback redundant.

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
| Hook-switching on `matchMedia` change causes stale state from the previously-active sub-hook | The inactive sub-hook’s state is ignored. Its listeners are disabled via its own `enabled` effect, preventing it from opening spontaneously. |
| `handleContextMenu: null` on mobile causes React warning | `onContextMenu={null}` is valid React and attaches no listener. |
| `useDesktopContextMenu` and `useMobileSelectionMenu` duplicate the dismiss effect (pointerdown + Escape) | The duplicated block is ~15 lines. Extracting a shared `useMenuDismiss` hook is deferred until a third menu variant is introduced. |

## Future Steps Enabled

- **Step 2 (mobile reducer)**: `useMobileSelectionMenu.js` is isolated; replacing `openedBySelectionRef` and `touchActive` with a state machine will affect only one file.
- **Step 4 (Floating UI positioning)**: Positioning logic can be added to both sub-hooks via a shared helper without modifying `ZenModeOverlay` or `BaseOverlay`.
- **Step 3 (shared overlay-menu contract)**: `DigestOverlay` will be able to call `useOverlayContextMenu` using the same interface as `ZenModeOverlay`.
