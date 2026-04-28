---
plan: plans/4-introduce-floating-ui-for-positioning-only.plan.md
last_updated: 2026-04-27 21:50, 41c60e8
---

# Introduce Floating UI For Positioning Only — Implementation Log

## Dependency

`@floating-ui/react-dom@2.1.8` added to `client/package.json` dependencies.

## Custom viewport math removed

Deleted from `OverlayContextMenu.jsx`:
- `MENU_WIDTH_PX`, `MENU_VERTICAL_PADDING_PX`, `MENU_ITEM_HEIGHT_PX`
- `clampMenuPosition(anchorX, anchorY, actionCount)`
- render-time `const position = clampMenuPosition(...)`

`MENU_EDGE_GAP_PX` kept; used as the `shift()` padding value.

## Virtual reference shape chosen

`useOverlayContextMenu.js` now produces a `positionReference` snapshot instead of raw `anchorX`/`anchorY` coordinates.

Shape:
```js
{
  kind: 'point' | 'range',
  boundingRect: { x, y, top, left, right, bottom, width, height },  // plain copied object
  clientRects: Array<same shape>,                                    // [] for point refs
  placement: 'bottom-start' | 'bottom',
  offsetPx: 0 | 12,
}
```

Helper functions added to the hook: `copyDomRect(rect)`, `createPointPositionReference(x, y)`.

Desktop right-click → point ref at `(event.clientX, event.clientY)` with zero-size `boundingRect`.

Mobile selection → range ref with bounding rect and client rects copied from `range.getBoundingClientRect()` and `range.getClientRects()` at selection-read time. Returns `null` if `clientRects` is empty, failing clearly rather than silently falling back.

## Contract pivot

`anchorX`/`anchorY` removed from:
- `CLOSED_MENU_STATE`
- `openMenu()` signature
- hook return value
- `overlayMenu` contract in `ZenModeOverlay`, `DigestOverlay`, `BaseOverlay`
- `OverlayContextMenu` props

No compatibility shim introduced.

## Floating UI wiring in OverlayContextMenu

`createVirtualReference(positionReference)` returns `{ getBoundingClientRect, getClientRects }`.

`useFloating()` configured with:
- `strategy: 'fixed'` — matches the portaled fixed menu
- `transform: false` — avoids collision with `animate-overlay-menu-enter` CSS transforms
- `whileElementsMounted: autoUpdate`
- Middleware: `inline()` for range refs only, `offset(offsetPx)`, `flip()`, `shift({ padding: 8 })`

`setMenuNode` callback ref merges `menuRef.current` (needed by `useOverlayMenuDismissal`) and `floatingRefs.setFloating`.

`visibility: isPositioned ? 'visible' : 'hidden'` prevents one-frame flash at (0,0).

## Verification

- `npm run build` ✓
- `CI=1 npm run lint` ✓ (no new errors; pre-existing warnings only)
- `npm ls @floating-ui/react-dom` → `@floating-ui/react-dom@2.1.8` ✓
- `rg "clampMenuPosition|MENU_WIDTH_PX|MENU_ITEM_HEIGHT_PX|MENU_VERTICAL_PADDING_PX" client/src` → no matches ✓
- `rg "@floating-ui/react-dom|useFloating|autoUpdate|shift\(|flip\(|inline\(" client/src/components/OverlayContextMenu.jsx` → imports and usage ✓
- `rg "anchorX=|anchorY=" client/src/components` → no matches ✓

## Visual differences

- Menu no longer left-aligns at the selection's horizontal midpoint; `placement: 'bottom'` + `inline()` centers it under the selected text range correctly.
- Viewport-edge collision handled by `flip()` + `shift()` instead of hard-coded clamp math.
- Entrance animation unchanged; `transform: false` ensures Floating UI doesn't apply transform-based positioning that would conflict with `animate-overlay-menu-enter`.
