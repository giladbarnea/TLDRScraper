---
last_updated: 2026-04-23 15:22
---

# Make Mobile Selection State Explicit Implementation Plan

## Overview

Implement the second item from `impl-review/review-1.md`: make the mobile native-text-selection path inside the overlay context menu explicit with a reducer.

This plan is intentionally the follow-up to `plans/1-split-mobile-and-desktop.plan.md`. The first plan separates desktop right-click from mobile selection. This plan then replaces the mobile path's implicit listener-local state with a named state machine so future mobile bugs become transition edits instead of more refs and flags.

## Current State Analysis

The current checked-in hook still has one combined owner in `client/src/hooks/useOverlayContextMenu.js`:

- `openedBySelectionRef` tracks whether close should clear selection.
- `touchActive` is a local variable inside the mobile effect.
- `selectionchange`, `touchstart`, and `touchend` encode transitions across separate handlers.
- The ghost-click guard is behavioral but implicit: when selection clears during a touch, the menu stays open so the later click can reach the menu action.

`plans/1-split-mobile-and-desktop.plan.md` defines the prerequisite shape:

- Keep one exported `useOverlayContextMenu`.
- Add internal `useDesktopContextMenu`.
- Add internal `useMobileSelectionMenu`.
- Add internal `useOverlayMenuDismissal`.
- Use source-aware menu state so shared dismissal knows whether a menu was opened by mobile selection.

This second plan should be implemented only after that split has landed. If `useMobileSelectionMenu` does not exist yet, implement and verify plan 1 first. Do not fold both plans into one larger refactor.

## Desired End State

After this plan is implemented:

- The mobile selection flow is represented by a pure reducer with named modes and events.
- `useMobileSelectionMenu` still owns DOM reads and document listeners, but transition decisions come from the reducer.
- The exported `useOverlayContextMenu` API remains unchanged.
- The visible menu behavior remains unchanged before any bug fixes:
  - Mobile selection inside `[data-overlay-content]` opens the menu after finger lift.
  - Selection changes while touching do not close the menu prematurely.
  - Tapping the menu action still preserves the selected text captured at open time.
  - Outside pointerdown closes the menu and clears native selection for mobile-selection-opened menus.
  - Escape closes the menu before `BaseOverlay` sees the same key event.
- Desktop right-click behavior remains owned by the desktop hook from plan 1.
- `BaseOverlay`, `DigestOverlay`, `OverlayContextMenu`, and `ElaborationPreview` behavior is not intentionally changed.

## Key Discoveries

- `client/src/hooks/useOverlayContextMenu.js` is the current complexity center. The mobile path's state is distributed across `openedBySelectionRef`, `touchActive`, and document listeners.
- `client/src/components/BaseOverlay.jsx` owns the shared DOM contract: `data-overlay-content` on the scroll surface and Escape yielding via `event.defaultPrevented`.
- `client/src/components/OverlayContextMenu.jsx` already consumes captured `selectedText`, which is required because mobile `touchstart` can collapse the live browser selection before click.
- `client/src/components/ZenModeOverlay.jsx` is the only current consumer of `useOverlayContextMenu`.
- `client/src/components/DigestOverlay.jsx` composes `BaseOverlay` but does not compose the context menu.
- Reducer style already exists under `client/src/reducers/`, especially `interactionReducer.js`, `gestureReducer.js`, and `summaryDataReducer.js`. The new reducer should follow that plain-object, pure-function style.

## What We Are Not Doing

- No desktop right-click changes.
- No Digest overlay context-menu wiring.
- No `BaseOverlay` contract relocation.
- No Floating UI or BaseUI migration.
- No focus/layer stack work.
- No pull-to-close restoration.
- No `OverlayContextMenu` positioning changes.
- No `ElaborationPreview` styling or Escape behavior changes.
- No cleanup of debug logging unless a log line directly prevents verification.
- No product behavior changes to the known mobile edge cases in this pass. Preserve first, then fix with targeted follow-up transitions.

## Implementation Approach

Add a small pure reducer for the mobile selection path and call it from `useMobileSelectionMenu`.

The reducer should own only mobile-selection lifecycle state. It should not read the DOM, call `window.getSelection()`, attach listeners, or mutate React state. The hook should continue to do all side effects:

- read current overlay selection
- call `openMenu`
- call `closeMenu`
- clear native selection when requested by shared dismissal
- attach and detach document listeners

Use the same "reducer returns a decision" style already used by `interactionReducer.js`, because event handlers need an immediate decision:

```js
const { state: nextState, decision } = reduceMobileSelectionMenu(currentState, event)
```

Then the hook executes the decision after updating the reducer state ref.

## Phase 1: Add The Mobile Selection Reducer

### Overview

Create a pure reducer that describes mobile selection modes and transitions in one file.

### Changes Required

#### 1. Add reducer module

**File**: `client/src/reducers/mobileSelectionMenuReducer.js`

Add exported constants and helpers:

```js
export const MobileSelectionMenuMode = Object.freeze({
  IDLE: 'idle',
  TOUCHING: 'touching',
  SELECTED_TOUCHING: 'selected-touching',
  OPEN: 'open',
  OPEN_TOUCHING: 'open-touching',
})

export const MobileSelectionMenuEventType = Object.freeze({
  TOUCH_STARTED: 'TOUCH_STARTED',
  TOUCH_ENDED: 'TOUCH_ENDED',
  SELECTION_OBSERVED: 'SELECTION_OBSERVED',
  SELECTION_CLEARED: 'SELECTION_CLEARED',
  MENU_CLOSED: 'MENU_CLOSED',
})

export const MobileSelectionMenuDecisionType = Object.freeze({
  NONE: 'NONE',
  OPEN_MENU: 'OPEN_MENU',
  CLOSE_MENU: 'CLOSE_MENU',
})
```

Use this state shape:

```js
{
  mode: MobileSelectionMenuMode.IDLE,
  selection: null,
}
```

Where `selection` is the hook-provided data object:

```js
{
  anchorX,
  anchorY,
  selectedText,
}
```

Add:

```js
export function createInitialMobileSelectionMenuState()
export function reduceMobileSelectionMenu(state, event)
```

The reducer returns:

```js
{
  state: nextState,
  decision: {
    type: MobileSelectionMenuDecisionType.NONE,
  },
}
```

or:

```js
{
  state: nextState,
  decision: {
    type: MobileSelectionMenuDecisionType.OPEN_MENU,
    selection,
  },
}
```

or:

```js
{
  state: nextState,
  decision: {
    type: MobileSelectionMenuDecisionType.CLOSE_MENU,
  },
}
```

Do not include a `CLEAR_SELECTION` decision in this reducer. Selection clearing is part of shared dismissal and action click behavior, not the mobile selection observer itself.

#### 2. Define behavior-preserving transitions

**File**: `client/src/reducers/mobileSelectionMenuReducer.js`

Implement these transitions:

| Current mode | Event | Next mode | Decision | Notes |
|---|---|---|---|---|
| `idle` | `TOUCH_STARTED` | `touching` | none | Native selection may be starting. |
| `touching` | `SELECTION_OBSERVED(selection)` | `selected-touching` | none | Store selection but do not open mid-touch. |
| `selected-touching` | `SELECTION_OBSERVED(selection)` | `selected-touching` | none | Update stored selection while handles move. |
| `touching` | `TOUCH_ENDED` with selection | `open` | open menu | Opens after finger lift. |
| `selected-touching` | `TOUCH_ENDED` with selection | `open` | open menu | Opens with latest selection. |
| `touching` | `TOUCH_ENDED` without selection | `idle` | none | No selected text. |
| `selected-touching` | `TOUCH_ENDED` without selection | `idle` | none | Selection disappeared before lift. |
| `idle` | `SELECTION_OBSERVED(selection)` | `open` | open menu | Covers non-touch selectionchange on coarse pointer. |
| `open` | `SELECTION_OBSERVED(selection)` | `open` | open menu | Reposition/update text after selection handle changes while not touching. |
| `open` | `SELECTION_CLEARED` | `idle` | close menu | Current behavior closes when selection clears and no touch is active. |
| `open` | `TOUCH_STARTED` | `open-touching` | none | Preserve open menu during action tap or range tap. |
| `open-touching` | `SELECTION_CLEARED` | `open-touching` | none | Current ghost-click guard: do not close mid-touch. |
| `open-touching` | `SELECTION_OBSERVED(selection)` | `open-touching` | none | Store latest selection while touching, do not reopen mid-touch. |
| `open-touching` | `TOUCH_ENDED` with selection | `open` | open menu | Update anchor/text after finger lift. |
| `open-touching` | `TOUCH_ENDED` without selection | `open` | none | Preserve current behavior so a menu-button click can still fire after selection collapsed on touchstart. |
| any | `MENU_CLOSED` | `idle` | none | Sync reducer when shared dismissal or action click closes menu. |

Keep default behavior boring:

```js
default:
  return { state, decision: NONE_DECISION }
```

#### 3. Add small pure reducer verification target

**File**: `client/src/reducers/mobileSelectionMenuReducer.js`

Add concise examples in comments only if they clarify the transition table. Do not add broad comments that restate every line.

## Phase 2: Wire The Reducer Into The Mobile Hook

### Overview

Replace local mobile transition state in `useMobileSelectionMenu` with reducer-driven decisions.

### Changes Required

#### 1. Import reducer symbols

**File**: `client/src/hooks/useOverlayContextMenu.js`

Import:

```js
import {
  MobileSelectionMenuDecisionType,
  MobileSelectionMenuEventType,
  createInitialMobileSelectionMenuState,
  reduceMobileSelectionMenu,
} from '../reducers/mobileSelectionMenuReducer'
```

Keep the public hook return unchanged:

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

#### 2. Add reducer dispatch helper inside `useMobileSelectionMenu`

**File**: `client/src/hooks/useOverlayContextMenu.js`

Inside the private `useMobileSelectionMenu` hook from plan 1, replace `let touchActive = false` with a reducer state ref:

```js
const mobileStateRef = useRef(createInitialMobileSelectionMenuState())

function dispatchMobileSelectionEvent(event) {
  const { state, decision } = reduceMobileSelectionMenu(mobileStateRef.current, event)
  mobileStateRef.current = state
  runMobileSelectionDecision(decision)
}
```

`runMobileSelectionDecision` should call existing hook commands:

```js
function runMobileSelectionDecision(decision) {
  if (decision.type === MobileSelectionMenuDecisionType.OPEN_MENU) {
    openMenu({
      source: MenuOpenSource.MOBILE_SELECTION,
      ...decision.selection,
    })
    return
  }

  if (decision.type === MobileSelectionMenuDecisionType.CLOSE_MENU) {
    closeMenu()
  }
}
```

This intentionally uses a ref because document listeners need the latest state synchronously and the reducer state does not drive rendering.

#### 3. Make selection reads declarative at the hook boundary

**File**: `client/src/hooks/useOverlayContextMenu.js`

Keep DOM reading in the hook:

```js
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
```

Do not move `[data-overlay-content]` ownership in this plan.

#### 4. Convert document handlers to events

**File**: `client/src/hooks/useOverlayContextMenu.js`

Convert handlers to dispatch reducer events:

```js
function handleTouchStart() {
  dispatchMobileSelectionEvent({
    type: MobileSelectionMenuEventType.TOUCH_STARTED,
  })
}

function handleTouchEnd() {
  dispatchMobileSelectionEvent({
    type: MobileSelectionMenuEventType.TOUCH_ENDED,
    selection: readOverlaySelection(),
  })
}

function handleSelectionChange() {
  const selection = readOverlaySelection()
  dispatchMobileSelectionEvent(
    selection
      ? { type: MobileSelectionMenuEventType.SELECTION_OBSERVED, selection }
      : { type: MobileSelectionMenuEventType.SELECTION_CLEARED }
  )
}
```

The hook should no longer contain:

```js
let touchActive = false
```

and no branch should ask:

```js
if (!touchActive) ...
```

Those decisions belong to `reduceMobileSelectionMenu`.

#### 5. Reset reducer state when the menu is closed externally

**File**: `client/src/hooks/useOverlayContextMenu.js`

Any close path that is outside the mobile reducer should also dispatch or directly reset mobile reducer state:

- `enabled -> false`
- shared outside pointerdown dismissal
- shared Escape dismissal
- `OverlayContextMenu` action click through `contextMenu.closeMenu`

The least invasive shape is to keep `closeMenu` as the single exported close command and let it notify mobile state:

```js
const resetMobileSelectionStateRef = useRef(() => {})

const closeMenu = useCallback((options) => {
  resetMobileSelectionStateRef.current()
  setMenuState(CLOSED_MENU_STATE)
}, [])
```

Then `useMobileSelectionMenu` can register:

```js
useEffect(() => {
  resetMobileSelectionStateRef.current = () => {
    mobileStateRef.current = createInitialMobileSelectionMenuState()
  }
  return () => {
    resetMobileSelectionStateRef.current = () => {}
  }
}, [])
```

Alternative acceptable shape: expose `resetMobileSelectionState` from the private mobile hook and call it from the coordinator. Keep it private to `useOverlayContextMenu.js`.

#### 6. Preserve shared dismissal semantics

**File**: `client/src/hooks/useOverlayContextMenu.js`

Do not change `useOverlayMenuDismissal` semantics from plan 1:

- Pointerdown inside the menu does nothing.
- Pointerdown outside closes the menu.
- Pointerdown outside clears native selection only when the open source is `MOBILE_SELECTION`.
- Escape calls `preventDefault()`, `stopPropagation()`, and `stopImmediatePropagation()`, then closes the menu.

The reducer should not own desktop dismissal, Escape arbitration, or native selection clearing.

## Phase 3: Documentation And Verification Notes

### Overview

Update docs only after the reducer behavior is implemented and verified.

### Changes Required

#### 1. Update client architecture docs

**Files**:

- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`

Document:

- `useOverlayContextMenu` still exports one overlay-menu primitive.
- Desktop and mobile paths are internally split.
- Mobile selection is now reducer-driven.
- The reducer owns modes/events/decisions, while the hook owns DOM reads and side effects.
- The `BaseOverlay` contracts remain unchanged.
- Digest remains the intended future consumer, not implemented here.

Do not manually edit YAML frontmatter timestamps.

#### 2. Add implementation log

**File**: `thoughts/26-04-07-context-menu-research/implementation/iteration-3.md`

Create a short implementation note after the change lands:

- what reducer was added
- what hook state it replaced
- which behaviors were verified
- any mobile bugs deliberately preserved for later targeted fixes

Do not turn the implementation note into a second plan.

## Acceptance Criteria

### Build And Search Verification

- [ ] `cd client && npm run build`
- [ ] `cd client && CI=1 npm run lint`
- [ ] `rg -n "let touchActive|openedBySelectionRef" client/src/hooks/useOverlayContextMenu.js`
  - Expected: no matches.
- [ ] `rg -n "reduceMobileSelectionMenu|MobileSelectionMenuMode|MobileSelectionMenuEventType" client/src`
  - Expected: reducer module plus hook import/use and docs.
- [ ] `rg -n "useOverlayContextMenu\\(" client/src`
  - Expected: `ZenModeOverlay` remains the only current call site.

Only fix failures introduced by this reducer work.

### Manual Verification

Desktop regression:

1. Open a Zen summary overlay.
2. Right-click in the prose body.
3. Confirm the custom menu opens at the cursor and the browser native menu does not.
4. Press Escape once and confirm only the menu closes.
5. Press Escape again and confirm the overlay closes.
6. Select text with the mouse, right-click, choose Elaborate, and confirm the selected text reaches `ElaborationPreview`.

Mobile or mobile emulation:

1. Open a Zen summary overlay.
2. Long-press still on text until native selection appears.
3. Lift finger and confirm the custom menu opens near the selected text.
4. Tap Elaborate and confirm the preview opens with the selected text.
5. Select text, drag selection handles, and confirm the menu does not close while the touch is active.
6. Tap outside the menu and confirm the menu closes and native selection clears.
7. Select text again, press Escape with a hardware keyboard or simulator shortcut, and confirm the menu closes before the overlay closes.

Regression checks:

1. Tap a normal article card with no overlay text selected and confirm summary open behavior still works.
2. Tap inside selected overlay prose and verify behavior matches pre-change behavior. Do not "fix" this unless a concrete bug is separately scoped.
3. Use bottom overscroll-up and confirm mark-removed behavior is unchanged.
4. Open a digest overlay and confirm it still has no context menu behavior.
5. Confirm `ElaborationPreview` Escape and backdrop close still affect only the preview layer.

## Risk Notes

- Mobile native selection is browser-owned state. The reducer must make the existing behavior explicit before changing it.
- `OPEN_TOUCHING` is important. It preserves the current guard where a touch on the menu action may collapse native selection before the click event fires.
- Do not use React render state as the only source for document-listener decisions. Keep a synchronized ref or reducer dispatch helper so capture-phase document handlers read the latest mode immediately.
- Keep `selectedText` capture at menu-open time. Removing it reintroduces the mobile race fixed in iteration 2.
- Do not let this reducer grow into a generic overlay menu reducer. It is only for mobile selection lifecycle.

## References

- `client/ARCHITECTURE.md`
- `client/STATE_MACHINES.md`
- `client/src/components/BaseOverlay.jsx`
- `client/src/components/DigestOverlay.jsx`
- `client/src/components/OverlayContextMenu.jsx`
- `client/src/components/ZenModeOverlay.jsx`
- `client/src/hooks/useOverlayContextMenu.js`
- `client/src/reducers/gestureReducer.js`
- `client/src/reducers/interactionReducer.js`
- `thoughts/26-04-07-context-menu-research/feature-map.md`
- `thoughts/26-04-07-context-menu-research/impl-review/review-1.md`
- `thoughts/26-04-07-context-menu-research/implementation/iteration-1.md`
- `thoughts/26-04-07-context-menu-research/implementation/iteration-2.md`
- `thoughts/26-04-07-context-menu-research/plans/1-split-mobile-and-desktop.plan.md`
