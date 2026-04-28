---
originates_from: impl-review/0-g-review-1.md
last_updated: 2026-04-28 15:22
---

# Adopt Floating UI Interaction Primitives For The Layer/Focus Stack

## Overview

Implement review item 5 ("Use a stack, not arbitration"). Replace per-component Escape arbitration with `@floating-ui/react`'s interaction primitives — `FloatingTree`, `FloatingNode`, `useDismiss`, and `FloatingFocusManager`. No custom layer/focus provider, no in-house focus trap.

**Why Floating UI, not a custom `OverlayLayerProvider`?**
Plan 4 already pulls in `@floating-ui/react-dom` for positioning. `@floating-ui/react` is a strict superset that adds the interaction primitives this step needs. Stack ordering, Escape-topmost, outside-press dismissal, focus trap, focus return, AnimatePresence-friendly transition timing — all already solved upstream. Building a project-owned provider would re-implement a focus trap (a known footgun: contenteditable, dynamic mutations, iframes, AnimatePresence exits) and add ~200 lines for code we'd own forever. Net change with FUI is reduction, not addition.

**Why not BaseUI Dialog/Menu?**
BaseUI replaces visual + interaction concerns at once — that's review item 7 (full migration). This step is interaction primitives only. FUI fits the seam without changing markup or actions.

**Mobile-first lens.** App is ~99% mobile. Three consequences:
- `BaseOverlay` does not trap focus. A focus trap inside a `fixed inset-0` reader is a no-op visually but interferes with native text selection.
- `OverlayContextMenu` does not auto-focus its first action on coarse pointers. Auto-focus collapses native selection before the action click runs (the exact regression review item 1 warns about).
- `ElaborationPreview` does trap focus (modal). Even on mobile, dialogs trap focus by convention — VoiceOver/TalkBack expect it.

This plan should land after `plans/4-introduce-floating-ui-for-positioning-only.plan.md`. If 4 has not landed, this plan absorbs the install (since `@floating-ui/react` re-exports `react-dom`'s positioning API) and the positioning work is independent.

## Current State Analysis

Three independent document keydown systems coordinate by event-suppression:

- `client/src/components/BaseOverlay.jsx:43` adds a document `keydown` listener that closes on Escape unless `event.defaultPrevented`.
- `client/src/hooks/useOverlayContextMenu.js:200` (`useOverlayMenuDismissal`) adds capture-phase `pointerdown` + `keydown`; Escape calls `preventDefault + stopPropagation + stopImmediatePropagation` so `BaseOverlay` yields.
- `client/src/components/ElaborationPreview.jsx:60` adds another capture-phase `keydown`.

Focus is also DIY:
- `OverlayContextMenu.jsx:21` manually focuses the first action on desktop.
- `ElaborationPreview.jsx:91` declares `role="dialog"` + `aria-modal` but neither traps nor returns focus.
- `BaseOverlay.jsx:65` is the full-screen reader shell with no focus management at all.

Surface contract from plan 3 is in place: `BaseOverlay` owns `data-overlay-content`, the surface `onContextMenu`, and the `OverlayContextMenu` render site. `ZenModeOverlay` builds the `overlayMenu` contract; `DigestOverlay` is mounted only while open and does not yet pass `overlayMenu` (3-b territory).

Portal click `stopPropagation` guards (`BaseOverlay.jsx:64`, `OverlayContextMenu.jsx:51`, `ElaborationPreview.jsx:78`) are about React-tree bubbling into `ArticleCard` — separate concern from Escape arbitration. They stay.

## Desired End State

- `<FloatingTree>` mounted once near the app root.
- `BaseOverlay`, `OverlayContextMenu`, `ElaborationPreview` each register as a `<FloatingNode>` and wire `useDismiss` for Escape (and outside-press where applicable).
- No project-source `document.addEventListener('keydown', …)` calls. No `event.defaultPrevented` arbitration. No `stopImmediatePropagation`.
- `useOverlayMenuDismissal` deleted entirely.
- `OverlayContextMenu` uses `FloatingFocusManager(modal: false)` with mobile-aware `initialFocus`/`returnFocus` so coarse pointers don't lose native selection.
- `ElaborationPreview` uses `FloatingFocusManager(modal: true, returnFocus: true)`.
- `ElaborationPreview`'s FloatingNode is bound to DOM presence, not `isOpen`, so the AnimatePresence exit window keeps the dialog as the topmost dismiss target.
- `overlayMenu` contract drops `menuRef` and any explicit outside-dismiss command.
- Visual layering, z-index classes, action sets, gestures, scroll progress, body scroll lock, zenLock — unchanged.

## Key Discoveries

- `FloatingTree`'s "topmost wins" works only for nodes inside the tree. `BaseOverlay` must be a `FloatingNode` so its dismiss yields when a menu/dialog is open above it.
- `useDismiss(context, { escapeKey, outsidePress })` calls `onOpenChange(open, event, reason)`. `reason` distinguishes `'escape-key'` from `'outside-press'` — exactly the discriminator the menu needs to decide whether to clear the native selection on close.
- `FloatingFocusManager` accepts `initialFocus={-1}` and `returnFocus={false}` — the dial we need on coarse pointers.
- `<AnimatePresence>` exit on `ElaborationPreview` keeps DOM mounted ~180ms after `isOpen` flips. Bind the FloatingNode + `useFloating({open})` to a local `mounted` flag flipped by `AnimatePresence.onExitComplete`, not directly to `isOpen`.
- React context (and FloatingTree's tree context) crosses portals, so a single tree provider covers `BaseOverlay`, the menu, and the preview even though all three portal to `document.body`.

## What We Are Not Doing

- No custom `OverlayLayerProvider`. No in-house focus trap or focus-stack primitive.
- No focus trap on `BaseOverlay`.
- No focus stealing on coarse pointers in `OverlayContextMenu`.
- No BaseUI migration (item 7).
- No Floating UI positioning work (plan 4).
- No Digest menu wiring or `/api/elaborate` generalization (3-b).
- No `pull-to-close` restoration (item 6) — but its adjacency is acknowledged in Risk Notes since the focus story we drop *would* have re-aggravated the same selection conflict.
- No mobile selection reducer changes.
- No visual or action-set redesign.
- No `zenLock` changes.
- No toast layer registration.
- No broad cleanup of `[ctxmenu]` / `[elaborate]` debug logs.

## Implementation Approach

Each phase is independently shippable: install dep → mount tree (no behavior change) → swap each layer onto FUI (one at a time, the prior layer's listener stays intact during the transition) → trim contract → docs.

The layering rule across phases:

```text
wrapper (Zen / Digest)        owns menu state + actions (unchanged)
BaseOverlay                   owns surface contract + reader-Escape FloatingNode
OverlayContextMenu            owns its own FloatingNode + dismiss + non-trapping focus manager
ElaborationPreview            owns its own FloatingNode + dismiss + trapping focus manager
FloatingTree (App root)       owns "which layer is topmost"
```

## Phase 1: Upgrade To `@floating-ui/react`

**Files:** `client/package.json`, `client/package-lock.json`, plus any existing `@floating-ui/react-dom` import sites if Plan 4 has already shipped.

Replace `@floating-ui/react-dom` with `@floating-ui/react`. The positioning APIs (`useFloating`, `autoUpdate`, `offset`, `flip`, `shift`, `inline`) re-export from this package unchanged.

**Why a replacement, not co-install?** Two packages with overlapping APIs invite drift and tree-shake confusion. The superset is the right primary.

## Phase 2: Mount `FloatingTree`

**File:** `client/src/App.jsx`

Wrap `AppContent` (only) in `<FloatingTree>` inside `<InteractionProvider>`:

```text
InteractionProvider
  ToastContainer        # sibling, unchanged
  FloatingTree
    AppContent
```

**Why is `ToastContainer` outside the tree?** Toasts aren't dismissible layers and never call `useFloatingNodeId` / `useDismiss`. Putting them under the tree adds noise and a fake structural rule ("don't register"). Sibling placement makes the boundary structural.

This phase has zero observable behavior change. It only makes the next three phases possible.

## Phase 3: `BaseOverlay` → `FloatingNode` + `useDismiss` (Escape only)

**File:** `client/src/components/BaseOverlay.jsx`

Wire:
- `const nodeId = useFloatingNodeId()` and wrap the existing portal output in `<FloatingNode id={nodeId}>...</FloatingNode>`.
- `const { context, refs } = useFloating({ open: true, onOpenChange })` where `onOpenChange(open) = !open && onClose()`. The `useFloating` call is "synthetic" — `BaseOverlay` is not anchored to anything; we only need the context for `useDismiss`/tree wiring.
- `const { getFloatingProps } = useInteractions([useDismiss(context, { escapeKey: true, outsidePress: false })])`.
- Spread `getFloatingProps()` onto the existing portal root `<div>`. Set its ref to `refs.setFloating`.

Delete:
- The keydown listener `function handleEscape` and its add/remove calls.
- The `event.defaultPrevented` early return and the contract comment.

Split the single `useEffect` so body-scroll-lock gets its own effect (it was bundled with the keydown wiring).

Keep: portal click `stopPropagation`, the `overlayMenu` surface wiring (sans `menuRef`, see Phase 6), pull-to-close, scroll progress, overscroll-up.

**Why `outsidePress: false`?** A full-viewport reader has no "outside" pointer surface; the only way to dismiss outside the reader is via Escape or the close/check buttons.

**Why no `FloatingFocusManager` on the reader?** Trapping focus in a viewport-sized container is either a no-op (focus is already trapped by the viewport) or actively harmful on mobile because the focus manager would compete with the OS selection UI. Reader's only "modal" responsibility is owning Escape and that comes from the FloatingNode + `useDismiss`.

## Phase 4: `OverlayContextMenu` + hook → `FloatingNode` + dismiss + non-trapping focus manager

### `client/src/components/OverlayContextMenu.jsx`

- `const nodeId = useFloatingNodeId()`. Parent linkage flows through the tree implicitly.
- The existing `useFloating` call (already used for positioning per plan 4 — or co-introduced here if plan 4 hasn't landed) gains `open: isOpen` and `onOpenChange` from the contract.
- `const { getFloatingProps } = useInteractions([useDismiss(context, { escapeKey: true, outsidePress: true })])`.
- Wrap render: `<FloatingNode id={nodeId}><FloatingFocusManager context={context} modal={false} initialFocus={isCoarse ? -1 : 0} returnFocus={!isCoarse}>...</FloatingFocusManager></FloatingNode>` where `isCoarse = matchMedia('(pointer: coarse)').matches` computed once on mount.
- Use `refs.setFloating` as the portal root ref. Spread `getFloatingProps()` onto the same node.

Delete:
- The `useEffect` that focuses `firstActionRef`. `FloatingFocusManager`'s `initialFocus` owns this.
- `firstActionRef` itself once `initialFocus` is index-based.

Keep: `clampMenuPosition` (or its plan-4 successor), action rendering, the action-click flow.

**Why `modal: false`?** A small action menu shouldn't disable Tab through the rest of the page. `modal: true` would trap focus in 1–3 buttons — annoying for keyboard users and overkill for the surface area.

**Why `initialFocus: -1` on coarse pointers?** Auto-focusing a button collapses native text selection before the user can tap the action. On desktop, index-0 focus is the normal keyboard handle.

**Why drop `firstActionRef`?** `FloatingFocusManager` resolves `initialFocus` by index against the focusable descendants. The DOM ref existed only for the manual focus call we just deleted.

### `client/src/hooks/useOverlayContextMenu.js`

Delete the entire `useOverlayMenuDismissal` helper hook plus its invocation. `useDismiss` replaces both pointerdown and keydown handling, and FloatingTree replaces the `stopImmediatePropagation` arbitration.

Replace the `closeMenu` exposure with one dismiss-aware handler:

```text
onOpenChange(open, _event, reason):
  if open: return
  closeMenu({
    clearSelection:
      reason === 'outside-press'
      && menuStateRef.current.source === MenuOpenSource.MOBILE_SELECTION,
  })
```

Return `onOpenChange` from the hook in place of `closeMenu` and `menuRef`. (Action clicks call `onOpenChange(false)` manually — see Phase 6.)

Delete the top-of-file `CONTRACT` comment (lines 23–32) about `defaultPrevented` / `stopImmediatePropagation`. The contract is now: "wire `onOpenChange` into `useDismiss`."

**Why is the clear-selection logic still hook-side?** Only the hook knows whether the menu was opened via desktop right-click or mobile selection. FUI just gives us the `reason` — turning that into a selection-clear decision is hook business.

**Why does `enabled → false` still close cleanly?** The existing `useEffect(() => { if (!enabled) closeMenu() }, [...])` keeps working: setting `enabled` false flips `isOpen` false, which unmounts the menu's `FloatingNode`. No extra wiring needed.

## Phase 5: `ElaborationPreview` → `FloatingNode` + dismiss + trapping focus manager + AnimatePresence-aware mount

**File:** `client/src/components/ElaborationPreview.jsx`

- `const nodeId = useFloatingNodeId()`.
- Track DOM presence separately from `isOpen`:
  ```text
  const [mounted, setMounted] = useState(false)
  if (isOpen && !mounted) setMounted(true)
  // <AnimatePresence onExitComplete={() => setMounted(false)}>
  ```
- `const { context, refs } = useFloating({ open: mounted, onOpenChange: (o) => !o && onClose() })`.
- `const { getFloatingProps } = useInteractions([useDismiss(context, { escapeKey: true, outsidePress: true })])`.
- Wrap render: `<FloatingNode id={nodeId}><AnimatePresence onExitComplete={...}>{isOpen && <FloatingFocusManager context={context} modal={true} returnFocus={true} initialFocus={closeButtonRef}>...</FloatingFocusManager>}</AnimatePresence></FloatingNode>`.
- Spread `getFloatingProps()` onto the dialog panel `<motion.div role="dialog">` (not the backdrop).
- Make the visible backdrop a `<div>` (or `<motion.div>`) instead of a `<button>`, with no `onClick`. Floating UI's `outsidePress` covers the dismissal.

Delete:
- The capture-phase `keydown` `useEffect`.
- The backdrop `<button>`'s `onClick={onClose}` and its `aria-label="Dismiss elaboration"`.

**Why bind `useFloating({ open })` to `mounted`, not `isOpen`?** During the ~180ms exit animation, the dialog DOM is still visually present. If we bind to `isOpen`, the FloatingNode unregisters synchronously and Escape during the exit window targets the reader instead of the (still-visible) dialog. Binding to `mounted` keeps the dialog as the topmost dismiss target until the animation actually completes.

**Why `modal: true` here but not on the menu?** Dialogs are real modal experiences. Trapping focus + returning focus is the convention; assistive tech expects it. The dialog is also large enough that Tab cycling inside it is a feature, not friction.

**Why drop the backdrop `<button>` semantics?** `useDismiss({ outsidePress: true })` already routes backdrop clicks/taps to dismissal. Keeping a `<button>` adds an extra tab stop and an accessibility duplicate of the close button.

## Phase 6: Trim The `overlayMenu` Contract

**Files:** `client/src/components/BaseOverlay.jsx`, `client/src/components/ZenModeOverlay.jsx`, `client/src/components/OverlayContextMenu.jsx` (and `DigestOverlay.jsx` only if 3-b has landed).

The contract becomes:

```text
overlayMenu
  isOpen
  positionReference   # plan-4 shape; falls back to anchorX/anchorY pre-plan-4
  selectedText
  handleContextMenu   # surface onContextMenu (desktop right-click)
  onOpenChange        # dismiss-aware close, see Phase 4
  actions
```

Drop `menuRef`, `closeMenu`, and any `handleOutsideDismiss`-style command. `OverlayContextMenu` uses `refs.setFloating` from its own `useFloating` for the portal root; the parent doesn't need a handle.

Action click in `OverlayContextMenu.handleActionClick` becomes:

```text
text = selectedText || window.getSelection()?.toString() || ''
window.getSelection()?.removeAllRanges()
onOpenChange(false)        # was: onClose()
action.onSelect(text)
```

**Why drop `menuRef` from the contract?** It existed exclusively for `useOverlayMenuDismissal`'s outside-pointer test (deleted in Phase 4). FUI does the test internally against its own floating ref.

**Why expose `onOpenChange` instead of `closeMenu`?** Contract becomes a single primitive that aligns with FUI's API. Action click and FUI dismiss both call the same close path; no parallel commands to keep in sync.

## Phase 7: Documentation And Research Trail

**Files:** `client/ARCHITECTURE.md`, `client/STATE_MACHINES.md`, `thoughts/26-04-07-context-menu-research/0-b-feature-map.md`.

Replace the "Cooperating contracts" / "Escape arbitration via `event.defaultPrevented`" section with the FloatingTree story:

- Reader, menu, and dialog each register as a `FloatingNode`. FUI tracks topmost; only the topmost node's `useDismiss` reacts to Escape and outside-press.
- BaseOverlay does not trap focus.
- OverlayContextMenu uses non-modal focus management; on coarse pointers, it does not steal initial focus (intentional asymmetry — protects native text selection).
- ElaborationPreview is a real modal dialog: focus trap + return focus.
- `event.defaultPrevented` and `stopImmediatePropagation` are no longer part of the overlay contract.
- `pull-to-close` remains disabled (item 6 territory). This plan no longer interacts with the same selection workflow that disabled it, since BaseOverlay no longer manages focus.

**File:** `thoughts/26-04-07-context-menu-research/implementation/5-add-real-layer-focus-stack-or-baseui-dialog-menu-primitive.md` (after landing).

Concise note: dep upgrade, listeners removed, focus behavior per layer, AnimatePresence race fix, mobile-coarse-pointer asymmetry, deferrals.

## Acceptance Criteria

### Automated

- [ ] `cd client && npm run build`
- [ ] `cd client && CI=true npm run lint`
- [ ] `cd client && npm ls @floating-ui/react`
- [ ] `cd client && npm ls @floating-ui/react-dom`
  - Expected: only as a transitive dep of `@floating-ui/react`, not a direct dep.
- [ ] `rg -n "stopImmediatePropagation" client/src` → 0
- [ ] `rg -n "defaultPrevented" client/src` → 0
- [ ] `rg -n "useOverlayMenuDismissal" client/src` → 0
- [ ] `rg -n "document.addEventListener\\('keydown'" client/src` → 0
- [ ] `rg -n "FloatingTree" client/src/App.jsx` → 1
- [ ] `rg -n "FloatingNode|useFloatingNodeId" client/src/components` → BaseOverlay, OverlayContextMenu, ElaborationPreview
- [ ] `rg -n "FloatingFocusManager" client/src/components` → OverlayContextMenu, ElaborationPreview only

Only fix build/lint failures introduced by this work.

### Manual (mobile-first)

Mobile / mobile emulation:

1. Open Zen overlay. Long-press text, release. Menu opens. Selection still highlighted. Focus has not moved into the menu.
2. Tap "Elaborate". Menu closes; dialog opens; focus moves to the dialog close button.
3. Tap dialog backdrop. Dialog closes; reader stays open.
4. Open menu, tap inside reader prose but outside the menu. Menu closes; native selection clears.
5. Open menu, then before tapping anywhere, scroll. Menu's outside-press should not fire on a scroll/touch-move (regression check).

Desktop:

6. Open Zen, press Escape: reader closes.
7. Open Zen, right-click in prose: menu opens; first action focused.
8. Press Escape with menu open: menu closes only; reader stays.
9. Press Escape with dialog open: dialog closes only; reader stays.
10. Click-and-drag-to-select text, right-click, choose Elaborate: dialog opens with the selected text, focus inside the dialog.
11. Tab inside dialog: focus cycles within the dialog (modal trap).
12. Close dialog: focus returns to reader (chevron or wherever it came from).

Cross-layer / regression:

13. Pull-to-close, overscroll-up, mark-removed: unchanged.
14. Digest: opens/closes via the existing chevron and check; right-click still does not open a custom menu (3-b territory).
15. Click menu/dialog elements: do not bubble into the underlying ArticleCard (portal `stopPropagation` retained).
16. Press Escape during the dialog's exit animation: idempotent — same dialog close path; reader does not close prematurely.

## Risk Notes

- `outsidePress` arbitration across nested nodes is FUI's job. Our flows never have menu + dialog open simultaneously (menu closes synchronously inside `handleActionClick` before the dialog opens). If that invariant breaks later, FUI's topmost-wins rule handles it; do not re-introduce manual arbitration.
- `AnimatePresence.onExitComplete` does not fire if the component unmounts mid-animation. If `ElaborationPreview` ever unmounts while exiting (e.g., parent overlay closes), the local `mounted` flag never flips false. Effect cleanup must reset it explicitly so the FloatingNode is unregistered.
- `pull-to-close` remains disabled (item 6). The original draft of this plan would have re-aggravated the underlying mobile-selection conflict by trapping focus on `BaseOverlay`. This revision sidesteps that — but item 6 still owns re-enabling pull-to-close, and that work should reverify selection after the focus story here is in place.
- Do not replace `zenLock` with FloatingTree. zenLock prevents two readers from opening at all; FloatingTree orders already-open layers. Different concerns.
- `@floating-ui/react` has its own peer-dep requirements. Verify alignment with the project's React 19 setup before landing.
- Action click clears native selection before invoking `onOpenChange(false)`. This is intentional — keep the order; clearing after close would race with React state-driven unmount.
- `stopPropagation` on portal roots stays. It is about React-tree click bubbling into `ArticleCard`, not Escape arbitration. Do not remove it.

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
- `client/src/hooks/useOverlayContextMenu.js`
- Floating UI React docs: https://floating-ui.com/docs/react
- `useDismiss`: https://floating-ui.com/docs/useDismiss
- `FloatingFocusManager`: https://floating-ui.com/docs/FloatingFocusManager
- `FloatingTree` / `FloatingNode`: https://floating-ui.com/docs/FloatingTree
