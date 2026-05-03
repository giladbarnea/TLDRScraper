---
name: client/context-menu
description: Client overlay context menu architecture and DOM/layer contracts.
last_updated: 2026-05-03 15:10, bb6b54a
---
# Client: Context Menu

[→ State Machines: Context Menu](../state-machines/context-menu.md)

## Overlay Context Menu

An overlay-level right-click / selection-triggered action menu shared by overlay readers. Both `ZenModeOverlay` and `DigestOverlay` compose `useOverlayContextMenu`, instantiate `useElaboration`, and pass an `overlayMenu` contract into `BaseOverlay`. The two consumers wire structurally-identical `Elaborate` actions; the only difference is the URL-list shape they pass to the hook (Zen: one URL; Digest: the digest's source URL list). See [State Machines: Context Menu](../state-machines/context-menu.md#19-overlay-context-menu) for the state machine and event model.

**Key modules:** `hooks/useOverlayContextMenu.js`, `hooks/useElaboration.js` (shared elaboration state + `AbortController` + POST `/api/elaborate`), `components/OverlayContextMenu.jsx`, `components/BaseOverlay.jsx` (explicit `overlayMenu` surface contract and render site), `components/ElaborationPreview.jsx` (presentational; rendered against the hook's state by each wrapper), `reducers/mobileSelectionMenuReducer.js` (mobile selection lifecycle as a pure reducer consumed by `useMobileSelectionMenu`)

### Cooperating contracts (important)

The menu contract is explicit: a wrapper owns a `useOverlayContextMenu` instance plus action definitions, then passes an `overlayMenu` object into `BaseOverlay`. When that contract is present, `BaseOverlay` owns the menu surface wiring, the `OverlayContextMenu` render site, and the `overlayLayers` render site used by `ElaborationPreview`.

1. **`data-overlay-content` DOM marker.** `BaseOverlay` tags its scroll/content surface with `data-overlay-content` only when `overlayMenu` is present. The mobile selection→menu path in `useOverlayContextMenu` bails out unless `window.getSelection().anchorNode` is inside a `[data-overlay-content]` subtree. This scopes the otherwise-global `selectionchange` / `touchstart` / `touchend` listeners to the opted-in overlay reading surface.
2. **Floating UI layer stack.** `App.jsx` mounts one `<FloatingTree>`. `BaseOverlay`, `OverlayContextMenu`, and `ElaborationPreview` each register as `FloatingNode`s, so `useDismiss()` gives Escape and outside-press ownership to the topmost open layer without project-owned arbitration.
3. **Focus ownership by layer.** `BaseOverlay` does not trap focus. `OverlayContextMenu` uses a non-modal `FloatingFocusManager` and intentionally skips initial focus on coarse pointers so native selection survives. `ElaborationPreview` is the only trapping layer (`modal={true}`) and returns focus on close.

### Triggers

- **Desktop**: `onContextMenu` on the `BaseOverlay` scroll surface (right-click) → menu anchored at cursor coordinates.
- **Mobile**: document-level `selectionchange` / `touchstart` / `touchend` listeners. The mobile selection lifecycle is a pure reducer (`reduceMobileSelectionMenu`) driven by these listeners. The hook dispatches `TOUCH_STARTED` / `TOUCH_ENDED { selection }` / `SELECTION_OBSERVED { selection }` / `SELECTION_CLEARED`; the reducer returns `OPEN_MENU` / `CLOSE_MENU` / `NONE` decisions. Menu opens on finger lift (`touchend`) when a non-empty text selection exists inside `[data-overlay-content]`. Menu re-closes automatically when the selection is cleared while the user is not touching. The reducer preserves the ghost-click guard: when `touchend` finds no selection but the menu is open (tap on a menu button collapsed it), the reducer returns `NONE` so the pending click still reaches the action handler.

### Close paths

Menu: Floating UI outside-press + Escape via `useDismiss()`, plus overlay close/unmount. Preview: Floating UI outside-press + Escape via `useDismiss()`. Reader: Escape via `useDismiss()` on `BaseOverlay` only when no child layer is open.

### Current actions

Both `ZenModeOverlay` and `DigestOverlay` wire a single `Elaborate` action with the same key, label, icon, and trampoline (`onSelect: runElaboration`). The action opens `ElaborationPreview` for the selected text. The only difference between the two consumers is the URL list passed to `useElaboration`: Zen sends `[url]`; Digest sends `data.articleUrls`. The backend always scrapes all URLs in parallel and feeds the concatenated bodies to the LLM as `<source-articles>`. Positioning now uses Floating UI in `OverlayContextMenu.jsx`: desktop opens from a point virtual reference at the cursor, while mobile selection opens from a range virtual reference copied from the native selection geometry. `inline()`, `offset()`, `flip()`, and `shift()` handle centering and viewport collision.

### Status / WIP notes

The implementation is the codex-branch base (`useOverlayContextMenu` with `data-overlay-content` scoping) augmented with Floating UI's `FloatingTree` / `FloatingNode` / `useDismiss` / `FloatingFocusManager` layer stack plus worktree-branch debug instrumentation for an ongoing mobile-selection bug hunt:
- Every branch of `useOverlayContextMenu` and `OverlayContextMenu.handleActionClick` emits `[ctxmenu] …` console.log lines.
- `lib/quakeConsole.js` has a `setInterval(() => console.log(''), 10_000)` heartbeat so the quake console stays visibly alive between events.

Known mobile-selection interactions that remain buggy and are pending a concrete bug list: long-hold-still, long-hold-then-drag, tapping inside the selected range, dragging selection boundaries to extend, and selections that span the top/bottom viewport edge. All affect (a) whether the menu appears, (b) where it appears, and/or (c) whether it closes prematurely. See `thoughts/26-04-07-context-menu-research/` for the research/plan history and the codex branch discussion in git for the architectural rationale.

---
