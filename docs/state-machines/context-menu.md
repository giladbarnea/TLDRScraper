---
name: state-machines/context-menu
description: State machine for the overlay context menu, including mobile selection reducers.
last_updated: 2026-05-02 11:36
---
# State Machines: Context Menu

[→ Client: Context Menu](../client/context-menu.md)

### 19. Overlay Context Menu

| | |
|---|---|
| **Pattern** | `useState` + synchronously-mirrored `useRef` + three private hooks coordinating document-level event listeners (capture phase). The mobile selection path is driven by a pure reducer (`reduceMobileSelectionMenu`) rather than listener-local flags. |
| **Files** | `hooks/useOverlayContextMenu.js`, `components/OverlayContextMenu.jsx`, `reducers/mobileSelectionMenuReducer.js` |
| **Scope** | Per-overlay hook instance — one per `ZenModeOverlay`, one per `DigestOverlay` |
| **Status** | WIP — mobile selection interactions still buggy (pending concrete bug list). Debug instrumentation (`[ctxmenu]` console.logs + `quakeConsole.js` heartbeat) is intentionally left in. |

#### Internal Composition

The exported `useOverlayContextMenu` is a thin coordinator that composes two private hooks in the same file:

- `useDesktopContextMenu({ enabled, openMenu })` — owns `onContextMenu` (desktop right-click) only.
- `useMobileSelectionMenu({ enabled, openMenu, closeMenu, resetMobileSelectionStateRef })` — owns `selectionchange` / `touchstart` / `touchend` (mobile native text selection) only. Transition decisions are delegated to `reduceMobileSelectionMenu` in `reducers/mobileSelectionMenuReducer.js`; the hook only does DOM reads, listener setup/teardown, and decision execution.

Dismissal is no longer project-owned. `OverlayContextMenu.jsx` wires `useDismiss()` from Floating UI for Escape and outside-press, and forwards those dismiss reasons into the hook's `onOpenChange(open, event, reason)` callback. The coordinator still owns `closeMenu()`, because only it knows whether a close should also clear the native selection.

#### State Shape

```js
{ isOpen: false, positionReference: null, selectedText: '', source: 'none' }
// source ∈ { 'none', 'desktop', 'mobile-selection' }   (MenuOpenSource)
// positionReference is null when closed, else:
// {
//   kind: 'point' | 'range',
//   boundingRect,
//   clientRects,
//   placement,
//   offsetPx,
// }
// plus one ref:
menuStateRef             // mirrors menuState so `onOpenChange(..., reason)` can read the
                         // authoritative open source before React commits. Mutated synchronously
                         // inside openMenu()/closeMenu(); a useEffect mirrors post-commit.
```

`source` is internal coordination state — it is **not** exposed from the hook's return value.

#### States

```
CLOSED  ──(right-click in overlay content)──►  OPEN (source=desktop)
CLOSED  ──(mobile: selection settled in [data-overlay-content] after touchend)──►  OPEN (source=mobile-selection)
OPEN    ──(outside press / Escape / selection cleared / enabled→false)──►  CLOSED
```

`menuStateRef.current.source` is the discriminator. On close:
- If `source === 'mobile-selection'` **and** the dismiss reason is `'outside-press'`: call `window.getSelection()?.removeAllRanges()` before closing.
- Otherwise: do not touch the selection.

Because `source` lives inside `menuState` (not a standalone ref), the right-click and mobile-selection paths can't leak their flag into each other — every `openMenu` call declares `source` authoritatively.

#### Events / Transitions

| Event | Source | Effect |
|---|---|---|
| `onContextMenu` on scroll surface | `useDesktopContextMenu` (via `BaseOverlay`'s `overlayMenu` contract, desktop right-click) | `preventDefault`; `openMenu({ source: 'desktop', positionReference: createPointPositionReference(clientX, clientY) })` |
| `touchstart` (capture, document) | `useMobileSelectionMenu` | Dispatches `TOUCH_STARTED` into `reduceMobileSelectionMenu`; reducer flips `isTouching=true`. Menu will not open or close mid-touch. |
| `touchend` (capture, document) | `useMobileSelectionMenu` (mobile finger lift) | Reads current `[data-overlay-content]` selection; dispatches `TOUCH_ENDED { selection }`. Reducer returns `OPEN_MENU` when a selection is present, `NONE` otherwise (preserving the ghost-click guard when the selection collapsed mid-tap). |
| `selectionchange` (document) | `useMobileSelectionMenu` (mobile selection handles) | Dispatches `SELECTION_OBSERVED` when a non-empty overlay selection exists, else `SELECTION_CLEARED`. Reducer decides: mid-touch → store or hold; idle and open → `CLOSE_MENU`; idle and closed → reposition/open via `OPEN_MENU`. |
| `outside-press` | `OverlayContextMenu` via `useDismiss()` | Calls `onOpenChange(false, event, 'outside-press')`. The coordinator clears the native selection only when the menu source was `mobile-selection`, then resets the mobile reducer. On coarse pointers, outside-press is wired to `'click'` instead of `'pointerdown'` so scroll starts do not dismiss the menu. |
| `Escape` | `OverlayContextMenu` via `useDismiss()` | Calls `onOpenChange(false, event, 'escape-key')`. Floating UI keeps the reader open because the menu is the topmost child `FloatingNode`. |
| `enabled → false` | coordinator effect | `closeMenu()` (also resets mobile reducer) |
| action button click | `OverlayContextMenu.handleActionClick` | Clear selection; `onOpenChange(false)`; invoke `action.onSelect()` |

#### DOM / Layer Contracts (cooperating with BaseOverlay)

1. **`data-overlay-content` marker** — `BaseOverlay` tags its scroll surface only when `overlayMenu` is present. `useMobileSelectionMenu`'s selection reader bails unless the selection's `anchorNode.parentElement.closest('[data-overlay-content]')` matches. Removing the attribute from an opted-in menu surface disables mobile selection-triggered menus; applying it too broadly turns unrelated selections into menu triggers.
2. **Floating UI tree registration** — `App.jsx` mounts one `FloatingTree`, `BaseOverlay` registers the reader as a `FloatingNode`, and `OverlayContextMenu` / `ElaborationPreview` register child `FloatingNode`s beneath it. This is what makes only the topmost open layer respond to Escape / outside-press. Remove the shared tree or move the preview outside the reader's subtree and dismissal ownership regresses back into manual arbitration.

#### Positioning + Layer Interactions

`OverlayContextMenu.jsx` now uses Floating UI for both positioning and dismissal/focus management.

- Desktop right-click opens from a **point virtual reference** created at the cursor.
- Mobile native text selection opens from a **range virtual reference** copied from `Range.getBoundingClientRect()` and `Range.getClientRects()` while the selection is still valid.
- `strategy: 'fixed'` matches the portaled fixed menu.
- `transform: false` avoids conflicting with the menu entrance animation, which already uses CSS transforms.
- Middleware order is:
  - `inline()` for range references only, so multi-line selections position against the actual inline range geometry.
  - `offset(positionReference.offsetPx)`.
  - `flip()`.
  - `shift({ padding: MENU_EDGE_GAP_PX })`.

This removes the old project-owned viewport clamp math. Desktop remains cursor-anchored; mobile selection is now genuinely centered under the selected range instead of left-aligned at a pre-centered X coordinate.

#### Actions (current set)

| Consumer | Action | Effect |
|---|---|---|
| `ZenModeOverlay` | `Elaborate` | Captures selected text, calls `runElaboration` from `useElaboration({ sourceMarkdown: summaryMarkdown, articleUrls: [url] })`, and opens `ElaborationPreview` |
| `DigestOverlay` | `Elaborate` | Captures selected text, calls `runElaboration` from `useElaboration({ sourceMarkdown: markdown, articleUrls })`, and opens `ElaborationPreview`. Identical action shape; only the URL list differs (Digest passes N source URLs vs Zen's one) |

#### Mobile selection reducer

`reducers/mobileSelectionMenuReducer.js` owns the mobile selection lifecycle as a pure reducer. The hook (`useMobileSelectionMenu`) keeps all side effects (DOM reads, listener setup, calling `openMenu`/`closeMenu`, clearing the native selection via shared dismissal). The reducer owns transition decisions only.

State shape:

```js
{ isTouching: false, isOpen: false, selection: null }
// selection, when non-null, is { selectedText, positionReference } produced by readOverlaySelection()
```

Events:

```
TOUCH_STARTED
TOUCH_ENDED       { selection: Selection | null }
SELECTION_OBSERVED { selection: Selection }
SELECTION_CLEARED
MENU_CLOSED       // dispatched implicitly via resetMobileSelectionStateRef from closeMenu
```

Decisions the reducer returns to the hook:

```
{ type: 'NONE' }
{ type: 'OPEN_MENU', selection }
{ type: 'CLOSE_MENU' }
```

Transition summary:

| Situation | State change | Decision |
|---|---|---|
| `TOUCH_STARTED` | `isTouching → true` | NONE |
| `TOUCH_ENDED` with selection | `isTouching → false`, `isOpen → true`, store selection | OPEN_MENU |
| `TOUCH_ENDED` with no selection | `isTouching → false` (keep `isOpen`/`selection`) | NONE (preserves ghost-click guard: click about to fire on menu action) |
| `SELECTION_OBSERVED` while touching | store selection | NONE (do not open mid-gesture) |
| `SELECTION_OBSERVED` while idle | `isOpen → true`, store selection | OPEN_MENU (opens or repositions) |
| `SELECTION_CLEARED` while touching | optionally clear `selection` | NONE |
| `SELECTION_CLEARED` while idle, menu open | reset to initial | CLOSE_MENU |
| `SELECTION_CLEARED` while idle, menu closed | reset to initial | NONE |
| `MENU_CLOSED` | reset to initial | NONE |

`closeMenu` in the coordinator calls `resetMobileSelectionStateRef.current()` before it clears selection or updates menu state. This keeps the mobile reducer in sync whenever an external path (`useDismiss()` outside-press, `useDismiss()` Escape, action click, `enabled → false`) closes the menu. The `MENU_CLOSED` event is implicit through this reset; it is exported on the event enum for completeness and for any future caller that wants to dispatch it explicitly.

`resetMobileSelectionStateRef` is a `useRef(() => {})` owned by the coordinator and populated by `useMobileSelectionMenu` once listeners are attached. On effect cleanup it is restored to a no-op so stale resets do not fire against a non-attached reducer.

#### Mobile nuances (known buggy — do not "fix by guessing")

All tied to iOS / Android native selection UI; handled with care because the hook coexists with a non-React selection state machine in the browser:
- Long-hold still vs. long-hold + drag vs. dragging selection handles to extend.
- Tapping the already-selected range (usually collapses and may collide with `handlePointerDown`'s `getSelection().removeAllRanges()`).
- Tapping a menu button while prose is still selected — `touchend` fires before `click`. The reducer's `TOUCH_ENDED` transition returns `NONE` when the selection has collapsed mid-tap, so the menu does not re-open in the gap before the action's `handleActionClick` runs. The captured `selectedText` on menu state is what the action uses anyway, so this is robust even if the live selection is empty by click time.
- Selections that start or end outside the viewport (`range.getBoundingClientRect()` / `getClientRects()` may report partially off-screen geometry; Floating UI keeps the menu visible via `flip()` / `shift()`, but the visual attachment can still feel imperfect near viewport edges).

These are instrumented (the `[ctxmenu]` logs in every branch) pending a concrete bug report.

---
