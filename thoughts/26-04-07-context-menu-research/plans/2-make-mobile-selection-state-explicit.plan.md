---
last_updated: 2026-04-24 08:03
---

# Make Mobile Selection State Explicit Implementation Plan

## Overview

Implement the second item from `impl-review/review-1.md`: make the mobile native-text-selection path inside the overlay context menu explicit with a reducer.

This plan is intentionally the follow-up to `plans/1-split-mobile-and-desktop.plan.md`, which has already separated desktop right-click from mobile selection. This plan replaces the mobile path's remaining listener-local transition state with a small pure reducer so future mobile bugs become transition edits instead of more refs and flags.

## Current State Analysis

The current checked-in hook already has the plan-1 split in `client/src/hooks/useOverlayContextMenu.js`:

- `useDesktopContextMenu` owns desktop right-click.
- `useMobileSelectionMenu` owns mobile native text selection.
- `useOverlayMenuDismissal` owns outside pointerdown and Escape.
- `menuState.source` tracks whether close should clear native selection.
- `touchActive` is still a local variable inside `useMobileSelectionMenu`.
- `selectionchange`, `touchstart`, and `touchend` still encode mobile transitions across separate handlers.
- The ghost-click guard is behavioral but implicit: when selection clears during a touch, the menu stays open so the later click can reach the menu action.

This plan should stay within that already-landed split. Do not fold in Digest wiring, BaseOverlay contract relocation, positioning, focus-stack, or pull-to-close work.

## Desired End State

After this plan is implemented:

- The mobile selection flow is represented by a pure reducer with a tiny explicit state record and named events.
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

- `client/src/hooks/useOverlayContextMenu.js` is the current complexity center. The mobile path's state is now mostly isolated, but the transition state is still split between `touchActive`, source-aware menu state, and document listeners.
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

The complexity-reducing design is deliberately smaller than a five-mode enum. The reducer owns only three facts:

```js
{
  isTouching: false,
  isOpen: false,
  selection: null,
}
```

That state is enough to preserve current behavior:

- `isTouching` gates side effects. While true, selection observations update reducer state but do not open or close the menu.
- `isOpen` gates close behavior. A cleared selection closes the menu only when the menu is open and the user is not touching.
- `selection` stores the latest observed selection snapshot, but action-click still uses the menu state's captured `selectedText` as today.

This makes the mobile path declarative without inventing more states than the behavior actually needs.

## Phase 1: Add The Mobile Selection Reducer

### Overview

Create a pure reducer that describes mobile selection transitions in one file.

### Changes Required

#### 1. Add reducer module

**File**: `client/src/reducers/mobileSelectionMenuReducer.js`

Add exported constants and helpers:

```js
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
  isTouching: false,
  isOpen: false,
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

#### 2. Define behavior-preserving transitions declaratively

**File**: `client/src/reducers/mobileSelectionMenuReducer.js`

Implement the reducer as a small transition map keyed by event type. Keep helper branches inside the event handlers instead of scattering them across DOM listeners:

```js
const NONE_DECISION = Object.freeze({
  type: MobileSelectionMenuDecisionType.NONE,
})

function openMenuDecision(selection) {
  return {
    type: MobileSelectionMenuDecisionType.OPEN_MENU,
    selection,
  }
}

const MOBILE_SELECTION_TRANSITIONS = Object.freeze({
  [MobileSelectionMenuEventType.TOUCH_STARTED]: (state) => ({
    state: { ...state, isTouching: true },
    decision: NONE_DECISION,
  }),

  [MobileSelectionMenuEventType.TOUCH_ENDED]: (state, event) => {
    if (!event.selection) {
      return {
        state: { ...state, isTouching: false },
        decision: NONE_DECISION,
      }
    }

    return {
      state: {
        isTouching: false,
        isOpen: true,
        selection: event.selection,
      },
      decision: openMenuDecision(event.selection),
    }
  },

  [MobileSelectionMenuEventType.SELECTION_OBSERVED]: (state, event) => {
    if (state.isTouching) {
      return {
        state: { ...state, selection: event.selection },
        decision: NONE_DECISION,
      }
    }

    return {
      state: {
        isTouching: false,
        isOpen: true,
        selection: event.selection,
      },
      decision: openMenuDecision(event.selection),
    }
  },

  [MobileSelectionMenuEventType.SELECTION_CLEARED]: (state) => {
    if (state.isTouching) {
      return {
        state: {
          ...state,
          selection: state.isOpen ? state.selection : null,
        },
        decision: NONE_DECISION,
      }
    }

    if (!state.isOpen) {
      return {
        state: createInitialMobileSelectionMenuState(),
        decision: NONE_DECISION,
      }
    }

    return {
      state: createInitialMobileSelectionMenuState(),
      decision: {
        type: MobileSelectionMenuDecisionType.CLOSE_MENU,
      },
    }
  },

  [MobileSelectionMenuEventType.MENU_CLOSED]: () => ({
    state: createInitialMobileSelectionMenuState(),
    decision: NONE_DECISION,
  }),
})
```

This transition map preserves the important current cases:

| Situation | Reducer behavior |
|---|---|
| Long-press selection is still in progress | Store observed selection, do not open mid-touch. |
| Finger lifts with selected text | Open menu with latest selection snapshot. |
| Selection changes while not touching | Open/reposition menu with latest selection snapshot. |
| Selection clears while not touching and menu is open | Close menu. |
| Selection clears while touching a menu action or selected range | Keep menu open; do not ghost-click underlying content. |
| Touch ends after action tap collapsed the selection | Keep menu open and emit no decision; the click handler can still run. |
| Shared dismissal or action click closes the menu | Reset reducer to initial state. |

Keep default behavior boring:

```js
const transition = MOBILE_SELECTION_TRANSITIONS[event.type]
if (!transition) return { state, decision: NONE_DECISION }
return transition(state, event)
```

#### 3. Add small pure reducer verification target

**File**: `client/src/reducers/mobileSelectionMenuReducer.js`

Add a tiny reducer verification target during implementation. At minimum, assert:

- touch start + observed selection + touch end with selection opens once with the latest selection.
- observed selection while not touching opens/repositions.
- open + touch start + selection cleared + touch end without selection keeps the menu open and emits no close decision.
- open + selection cleared while not touching emits `CLOSE_MENU`.
- `MENU_CLOSED` resets to the initial state.

Prefer committed test coverage if the client already has a test pattern by implementation time. Otherwise, run a small transient Node script during implementation and record the result in the implementation note.

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

const closeMenu = useCallback(({ clearSelection = false } = {}) => {
  resetMobileSelectionStateRef.current()
  if (clearSelection) window.getSelection()?.removeAllRanges()
  menuStateRef.current = CLOSED_MENU_STATE
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
- The reducer owns state fields, events, and decisions, while the hook owns DOM reads and side effects.
- Reducer verification covers the ghost-click-preservation path.
- The `BaseOverlay` contracts remain unchanged.
- Digest remains the intended future consumer, not implemented here.

Do not manually edit YAML frontmatter timestamps.

#### 2. Add implementation log

**File**: `thoughts/26-04-07-context-menu-research/implementation/iteration-3.md`

Create a short implementation note after the change lands:

- what reducer was added
- what hook state it replaced
- what reducer verification was run
- which behaviors were verified
- any mobile bugs deliberately preserved for later targeted fixes

Do not turn the implementation note into a second plan.

## Acceptance Criteria

### Build And Search Verification

- [ ] `cd client && npm run build`
- [ ] `cd client && CI=1 npm run lint`
- [ ] `rg -n "let touchActive|openedBySelectionRef" client/src/hooks/useOverlayContextMenu.js`
  - Expected: no matches.
- [ ] `rg -n "reduceMobileSelectionMenu|MobileSelectionMenuEventType|MobileSelectionMenuDecisionType" client/src`
  - Expected: reducer module plus hook import/use and docs.
- [ ] Reducer verification for the transition cases listed in Phase 1.
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
- `isOpen && isTouching` is important. It preserves the current guard where a touch on the menu action may collapse native selection before the click event fires.
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
