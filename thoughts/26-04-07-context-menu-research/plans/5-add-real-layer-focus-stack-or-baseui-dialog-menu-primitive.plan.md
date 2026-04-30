---
name: Abstract: Adopt Floating UI Interaction Primitives For The Layer/Focus Stack
last_updated: 2026-04-30 17:19, 4e222f3
---

# Abstract: Adopt Floating UI Interaction Primitives For The Layer/Focus Stack

Replaces per-component Escape arbitration and DIY focus management with `@floating-ui/react`'s interaction primitives (`FloatingTree`, `FloatingNode`, `useDismiss`, `FloatingFocusManager`).

## Relevant Context
- Upgrades `@floating-ui/react-dom` → `@floating-ui/react` (superset, re-exports positioning APIs).
- `<FloatingTree>` mounted once at app root; `BaseOverlay`, `OverlayContextMenu`, and `ElaborationPreview` each register as `<FloatingNode>`.
- `useDismiss` replaces all project-source `document.addEventListener('keydown', …)` calls — no more `event.defaultPrevented` arbitration or `stopImmediatePropagation`.
- `FloatingFocusManager` with intentional mobile/desktop asymmetry: non-modal on menu (coarse pointers preserve native selection via `initialFocus: -1`), modal with return-focus on `ElaborationPreview`.
- `AnimatePresence` exit window on `ElaborationPreview` handled via `mounted` state flag so the dialog remains topmost dismiss target during the ~180ms animation.
- `useOverlayMenuDismissal` deleted entirely; `overlayMenu` contract drops `menuRef` and `closeMenu`, adds `onOpenChange`.
