---
last_updated: 2026-05-29 12:02
---

# Liquid Glass — Mental Model

## Core idea
Not a material. **A digital meta-material that bends light** (lensing) + **moves like liquid** (gel-flex motion). Job: define a hierarchy layer floating *above* content, deferring to it while staying readable.

## One-line definition
A floating, rounded, adaptive shape that **refracts** the content beneath it, **flexes** on touch, and **morphs** between states — all while changing its own tint/light/dark to remain legible.

## Anatomy (the layers that produce the look)
1. **Lensing** — interior refraction/distortion of content seen through the body (not just rim warping). The defining cue.
2. **Highlights** — specular rim from a simulated light environment, sometimes motion-aware.
3. **Shadow** — adaptive opacity (darker over text, lighter over solid bg) for grounding + separation.
4. **Tint adaptation** — surface and glyphs flip light↔dark (small elements only) based on what's behind.
5. **Internal illumination on touch** — glow spreads from the fingertip, bleeds onto nearby glass.
6. **Scroll edge effect** — soft dissolve (or hard cut for pinned headers) where content goes under the glass.

## Two variants — never mix
| | **Regular** | **Clear** |
|---|---|---|
| Use | Default. Anywhere. | Only over media-rich, bold, bright content. |
| Adaptive (L↔D, tint shift) | Yes | No |
| Transparency | Dynamic | Permanently high |
| Needs dimming layer under it | No | Yes (global or localized) |
| Content on top | Anything | Bold/bright only |

Clear requires *all three*: media-rich background, content layer tolerates dimming, foreground is bold+bright. Otherwise → Regular.

## Size behavior (same material, different mass)
- **Small** (nav/tab/buttons): flips L↔D fully; thinner; subtler lensing.
- **Large** (menus, sidebars, players): thicker; richer shadows; pronounced lensing; ambient color spill from nearby content; does **not** flip L↔D (too distracting at that area).

## Where to use it
**Yes:** the navigation/control plane floating above content — nav bars, tab bars, toolbars, toolbars→menus, sliders, sheets, sidebars, lock-screen controls, transient overlays (toast).
**No:** the content layer itself (tables, cards, list rows). Putting content in glass muddies hierarchy.

## Do / Don't (sharp rules)
- **Don't** stack glass on glass. Children on a glass surface use **fills/transparency/vibrancy**, not glass.
- **Don't** mix Regular and Clear in the same surface set.
- **Don't** tint everything. Tint only **primary** actions; let tint generate a content-aware range of tones, not a flat solid fill.
- **Don't** use solid opaque fills on a glass control — kills its character.
- **Don't** let content intersect glass at rest. Reposition/scale instead.
- **Do** keep glass content minimal — material is already visually rich.
- **Do** rely on **interior distortion**, not just rim sparkle, to do real hierarchy work.
- **Do** treat morphing (button → menu pops in place) as a first-class transition.
- **Do** honor Reduce Transparency / Increase Contrast / Reduce Motion — these are built-in modifiers, not separate styles.

## Project-specific override (from `accumulated-wisdom.md`)
This app has a **neutral light-gray background**, so the pure transparent treatment reads weak/decorative. Local rule: prefer a **"solid Liquid Glass"** flavor → near-white, slightly translucent, internal vertical gradient, bright top ridge, soft bottom rim, modest blur, moderate brightness lift, real interior SVG displacement. Heavy blur = plastic. Rim-only = inert. Reference specimen: `ToastContainer` via `LiquidGlassSurface` + `LiquidGlassDefs`.

## Diagnostic checklist (when a surface feels off)
1. Weak/decorative → switch to solid variant.
2. Plastic → lower opacity or blur.
3. Foggy → reduce blur first.
4. Background still competing → more brightness/dampening or interior distortion.
5. Glossy not glassy → rim works, interior doesn't.
6. Busy → strip labels/icons/tint before re-tuning material.

## One-sentence north star
**Liquid Glass is a hierarchy tool, not decoration:** a single floating, light-bending plane that stays out of the way of content until you touch it, then comes alive.
