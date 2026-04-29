---
name: Adopt Floating UI Interaction Primitives For The Layer/Focus Stack
done: 2026-04-29, working-tree
follows: implementation/4-introduce-floating-ui-for-positioning-only.md
implements: plans/5-add-real-layer-focus-stack-or-baseui-dialog-menu-primitive.plan.md
last_updated: 2026-04-29 14:59
---

# Layer / Focus Stack Implementation Log

The implementation mostly followed the plan, but one architectural adjustment turned out to matter more than the rest: `ElaborationPreview` could not remain merely a sibling rendered by `ZenModeOverlay` or `DigestOverlay` if we wanted Floating UI's parent/child dismissal semantics to be real rather than nominal.

That is why `BaseOverlay` gained `overlayLayers`. The important outcome is not the extra prop itself; it is that `BaseOverlay`, `OverlayContextMenu`, and `ElaborationPreview` now participate in one actual Floating UI subtree. Without that, `FloatingTree` would have existed, but the preview would still have behaved like an adjacent portal layer rather than a child layer in the stack.

A second decision was to keep `BaseOverlay` on the tree even though it is not positioned relative to anything. `useFloating` there is effectively a synthetic context carrier for `useDismiss`, not a positioning primitive. This is slightly less aesthetically pure than a bespoke reader-layer abstraction, but it is precisely the tradeoff the plan argued for: tolerate one mildly unusual use of the library in exchange for deleting project-owned dismissal arbitration.

The biggest small drift from the plan was coarse-pointer outside dismissal in `OverlayContextMenu`. The plan framed outside press in terms close to the existing eager pointer behavior, but touch scrolling is a harsher constraint than desktop clicking. Using coarse-pointer `click` rather than `pointerdown` preserves the manual invariant that beginning a scroll gesture should not instantly dismiss the menu. That choice came from the product behavior we need, not from a desire for API symmetry.

The focus split also landed with a stronger asymmetry than the plan may initially read as implying. `OverlayContextMenu` is intentionally not "keyboard-first on every device"; on coarse pointers, preserving the native selection is the primary requirement and focus must yield to it. `ElaborationPreview` is the opposite: once opened, it is a real modal surface, so trapping and returning focus is not polish but ownership.

`ElaborationPreview`'s `isMounted` state was not optional bookkeeping. It is what prevents the exit-animation window from punching a temporary hole in the layer stack. During that window the preview is still visually present, so it must still be the topmost dismiss target. This is one of the few places where the implementation burden came less from app code and more from reconciling `AnimatePresence` timing with the floating-layer model.

The menu contract did simplify, but not all the way down to a generic open/close primitive. `onOpenChange` replaced the older imperative dismissal surface, yet `useOverlayContextMenu` still owns the final close policy because it alone knows whether a close should clear native selection. In other words, dismissal transport moved into Floating UI, while selection semantics stayed local.

One subtle cleanup benefit is that the old coordination mechanism disappeared from the architecture narrative as well. Before this step, the docs had to teach an event-phase treaty between `BaseOverlay` and `useOverlayContextMenu`. After this step, the interesting thing to explain is no longer which listener suppresses which other listener, but which layer owns dismissal and why.

`ToastContainer` stayed outside `FloatingTree`, exactly as planned. That boundary is worth keeping explicit. Toasts are not part of the reader/menu/preview ownership stack, and letting them sit outside the tree makes that a structural fact instead of a convention.

Overall, the implementation did not expose any need for a project-owned layer provider or a premature BaseUI migration. The remaining complexity is still in mobile selection behavior, not in layer ownership. That is a good sign: the plan's goal was not to make the feature simple in every dimension, but to stop spending complexity budget on the wrong dimension.
