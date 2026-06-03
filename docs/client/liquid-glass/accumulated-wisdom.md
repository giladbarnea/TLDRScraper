---
name: client/liquid-glass
description: Liquid Glass design guidance for client surfaces, starting from the toast reference implementation.
last_updated: 2026-06-03 14:10
---
# Client: Liquid Glass

[→ State Machines: Toast](../state-machines/toast.md)

## Scope

This document captures the current working guidance for Liquid Glass client surfaces. The first converged implementation still lives in the global toast surface, but the material shell has now been extracted so future work can reuse it without copying toast code:
- `client/src/components/ToastContainer.jsx`
- `client/src/components/SelectionActionDock.jsx`
- `client/src/components/visual-effects/LiquidGlassSurface.jsx`
- `client/src/components/visual-effects/LiquidGlassDefs.jsx`
- `client/src/index.css` (`.liquid-glass-surface` and its data-attribute presets)

Treat the toast as the reference specimen before generalizing the design to other surfaces. The bottom selection dock (`SelectionActionDock.jsx`) is the second converged surface and confirms the shell generalizes cleanly to control-plane surfaces, not just transient overlays.

## What worked

### 1. On neutral backgrounds, use the solid variant

The fully translucent look depends on colorful or high-contrast content behind the surface. On this app's light gray background, that treatment quickly turns weak or decorative.

For notifications and similar overlays, the better target is a **solid Liquid Glass** variant:
- near-white surface
- still slightly translucent
- visible internal vertical gradient
- bright upper specular ridge
- softer lower shadow rim
- soft elevation shadow

If the surface reads as a pasted sticker, it is usually too flat. If it reads as cheap plastic, it is usually too opaque.

### 2. Optimize for attention dampening, not maximum blur

The goal is not to erase the background. The goal is to let the surface win the hierarchy while still feeling embedded in the scene.

The successful recipe was:
- moderate translucency
- a stronger top-to-bottom white gradient
- backdrop brightness lift
- enough distortion to soften background competition
- only modest literal blur

Heavy blur made the toast feel hazy and plastic. Moderate blur plus brightness and distortion kept the background present but less competitive.

### 3. Internal distortion matters more than rim-only tricks

A distortion effect that only acts at the perimeter can look technically correct but visually inert.

A better lever is a filter that warps the **content seen through the body of the surface**. For example, an SVG displacement filter applied through `backdrop-filter: url(...)` can bend underlying text or icons across the visible interior of the component. That kind of distortion does real hierarchy work: it keeps the background readable as context, but no longer readable enough to compete with the foreground label.

Use rim highlights and shadow rings to sell curvature, but rely on interior distortion when the goal is substantial glass rather than glossy chrome.

### 4. Minimal content helps the material read correctly

Liquid Glass already carries visual richness. The content inside it should be reduced, not embellished.

For the toast, the cleaner direction was:
- title only
- no brand tint
- no checkmark
- no secondary "summary ready" label

When the material is doing enough work, extra UI chrome fights it.

## Browser strategy

The base appearance must stand on its own without SVG-backed backdrop distortion.

Use progressive enhancement:
1. Base layer: gradient, translucency, specular rim, shadow, modest backdrop blur/brightness.
2. Enhanced layer: SVG-driven backdrop distortion in browsers that support `backdrop-filter: url(...)`.
3. Alive layer: optional `LiquidGlassTouchLight` child. WebGL canvas that paints a press-anchored radial glow inside the surface. Drop in as a child of any `LiquidGlassSurface`; it auto-attaches to its parent's pointerdown. Silent when `prefers-reduced-motion`, `prefers-reduced-transparency`, or no WebGL context.

Do not make the design depend on any layer above the base for basic quality. Some browsers will silently fall back to the base material.

## Alive layer constraints

When opting a surface into `LiquidGlassTouchLight`:
- Give the surface `overflow: hidden` so the canvas's `border-radius: inherit` clip is enforced.
- Lift the surface's text/children above the canvas with `position: relative; z-index: 1`. The canvas sits at z-index 0 inside the surface.
- Do not stack two touch-light canvases on overlapping glass — the effect is per-surface, not per-tree.

## Practical heuristics for future surfaces

When a new Liquid Glass surface feels wrong, check these in order:

1. **Too decorative / too weak** → it likely wants the solid variant rather than the airy translucent one.
2. **Too plastic** → reduce opacity or reduce blur.
3. **Too foggy** → reduce blur before changing anything else.
4. **Background still too loud** → increase brightness/dampening or add interior distortion.
5. **Looks glossy but not glassy** → the rim may be working, but the interior is not doing enough.
6. **Foreground feels busy** → remove labels, icons, and tint before tuning the material further.

## Design stance

Liquid Glass should behave like a hierarchy tool, not like decoration. The point is to create a surface that feels substantial, integrated, and quietly premium while letting foreground content stay immediately legible.
