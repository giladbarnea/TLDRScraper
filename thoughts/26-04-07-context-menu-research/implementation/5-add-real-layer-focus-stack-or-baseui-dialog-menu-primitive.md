---
name: Abstract: Adopt Floating UI Interaction Primitives For The Layer/Focus Stack
done: 2026-04-29, working-tree
follows: implementation/4-introduce-floating-ui-for-positioning-only.md
implements: plans/in-detail/5-add-real-layer-focus-stack-or-baseui-dialog-menu-primitive.plan.md
last_updated: 2026-04-30 17:19, 4e222f3
---

# Abstract: Layer / Focus Stack Implementation Log

Adopts `@floating-ui/react` interaction primitives to replace hand-rolled Escape arbitration and focus management. Followed the plan closely with one architectural adjustment and a few deliberate drifts.

## Key Changes
- `BaseOverlay` gained `overlayLayers` so `OverlayContextMenu` and `ElaborationPreview` participate in one actual Floating UI subtree, not just nominal parent/child.
- `BaseOverlay` stays on the tree with a synthetic `useFloating` call — a context carrier for `useDismiss`, not a positioning primitive.
- Coarse-pointer outside dismissal in `OverlayContextMenu` uses `click` events rather than `pointerdown`, preserving the invariant that scroll-start does not instantly dismiss the menu.
- `ElaborationPreview`'s `isMounted` state prevents the exit-animation window from punching a hole in the layer stack.
- `onOpenChange` replaced the older imperative dismissal surface, but `useOverlayContextMenu` still owns the close policy (selection-clear decision stays local).
- `ToastContainer` stays outside `FloatingTree` as a structural boundary.
