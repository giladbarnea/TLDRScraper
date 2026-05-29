---
plan: null
last_updated: 2026-05-29 12:02
---

# Liquid Glass toast extraction — implementation notes

## Scope landed

This pass kept the toast behavior intact while extracting the Liquid Glass material into a reusable shell. The toast remains the reference specimen, but the material is no longer encoded as a toast-only class.

## Decisions

`client/src/components/visual-effects/LiquidGlassSurface.jsx` is intentionally small. It is not a platform primitive or a design-system abstraction; it only centralizes the material boundary and exposes a few recipe axes: variant, depth, and lens.

`client/src/components/visual-effects/LiquidGlassDefs.jsx` now owns the shared SVG filter definitions so future glass surfaces can opt into the same lensing without smuggling SVG defs through `ToastContainer.jsx`.

The extracted CSS in `client/src/index.css` preserves the current solid compact preset almost verbatim. The important change is semantic: the recipe is now a material preset on `.liquid-glass-surface`, not a toast class.

The persistent mock toast was removed rather than repurposed. Keeping a demo specimen in the runtime component would have made future refactors harder to trust and would have kept the component split blurry.

The toast payload in `client/src/lib/toastBus.js` was tightened to the fields the UI actually consumes. `client/src/store/articleStore.js` still emits the toast, but no longer passes an unused `url`.

## Useful docs

`docs/client/liquid-glass/accumulated-wisdom.md` was the main design guide for preserving the current material character while extracting it.

`docs/client/liquid-glass/meet-liquid-glass-video-transcript.md` was useful as a vocabulary check, especially around size-dependent material changes and keeping Liquid Glass as a hierarchy tool rather than decoration.

`docs/state-machines/toast.md` needed drift correction because the toast emitter had already moved to `summaryActions.fetch` in `client/src/store/articleStore.js`.

## Follow-up stance

This extraction should make the next Liquid Glass steps cheaper, but it should not be overextended into a framework. New surfaces should reuse the shell only when they truly share the same material logic; visual language above that layer should stay local until repeated pressure proves otherwise.
