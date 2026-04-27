---
name: Make Mobile Selection State Explicit
implements: plans/2-make-mobile-selection-state-explicit.plan.md
last_updated: 2026-04-24 18:46
---

## Decisions

**Reset registration co-located with the listener effect.** The plan proposed a separate `useEffect(() => {}, [])` inside `useMobileSelectionMenu` to register `resetMobileSelectionStateRef`. Instead, registration happens at the top of the listener effect body, next to the freshly-created `mobileStateRef`. The plan's "alternative acceptable shape" explicitly permitted this; co-locating the ref and its reset closure keeps them on the same lifetime.

**Reducer state is a plain object ref, not React state.** `mobileStateRef` lives in the effect closure rather than in component state. Document listeners need synchronous reads — a `useRef` with synchronous writes inside `dispatchMobileSelectionEvent` is the right tool. The canonical source for menu open/close remains `menuState` React state; the reducer ref is only the mobile decision machine.

**`MENU_CLOSED` is on the enum but never dispatched explicitly.** Reset always happens through `closeMenu` → `resetMobileSelectionStateRef.current()`, which hard-resets `mobileStateRef.current` rather than running a reducer transition. The event is exported for any future caller that wants declarative dispatch, but the current wiring doesn't use it.

## Drift from plan

Plan suggested `SELECTION_CLEARED` while touching and `isOpen` should retain the snapshot as `selection: state.isOpen ? state.selection : null`. Implemented verbatim. Added a verification case that was not in the plan's listed cases (covering the `isOpen=false` + touching + cleared branch).

## Build & search verification

- `npm run build` — passed.
- `CI=1 npm run lint` — no new warnings.
- `rg "let touchActive|openedBySelectionRef"` on the hook — no matches.
- `rg "useOverlayContextMenu\("` in `src` — `ZenModeOverlay` remains the only call site.
- All five plan-specified reducer transitions verified via a transient Node script before wiring.
