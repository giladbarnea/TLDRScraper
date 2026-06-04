---
last_updated: 2026-06-04 16:27
---

# Weak-path Liquid Glass: from "puffy pill" to "flat plate"

What moved the surface from a glossy translucent pill to something that reads
like Apple's **opaque** Liquid Glass context menu — using only CSS that works on
all iOS browsers (WebKit): blur, a white gradient, and box-shadow. No SVG
displacement, no WebGL.

Five changes, each mapped to one observed difference from the real iOS menu.

## 1. Flat plate, not a thick rounded pill

The biggest single win. The old recipe faked a thick glass cross-section with
**interior curvature shadows** — a bright inner top glow and a dark inner bottom
rim — which made the surface bulge like a lozenge.

```css
/* before — simulates a thick, rounded glass body */
box-shadow:
  inset 0 0 0 0.5px   rgba(0,20,40,.13),
  inset 0 1.5px 0 -.25px  #fff,
  inset 0 14px 16px -10px #fff,        /* top bulge highlight */
  inset 0 -1.25px 0 -.5px rgba(0,20,40,.15),
  inset 0 -10px 14px -8px rgba(0,20,40,.13),  /* bottom bulge shadow */
  0 1px 2px 0   rgba(0,20,40,.09),
  0 14px 36px -4px rgba(0,20,40,.16);  /* elevation drop shadow */

/* after — a thin plate: faint edge + a single hairline top highlight */
box-shadow:
  inset 0 0 0 0.5px rgba(0,20,40,.10),
  inset 0 1px 0 -.25px rgba(255,255,255,.90);
```

**Lesson:** thickness in glass is sold by *interior* shading. Remove the inner
glows/rims and the same silhouette instantly reads as a few-mm-thin sheet. Apple's
opaque menu is a flat plate; the rounded corners stay, the rounded *body* goes.

## 2. More opaque, more milky

Apple's opaque variant oppresses the content under it far more than a "clear"
glass would. We raised the gradient's peak white from **35% → 63%**. Below ~50%
it reads as decorative film; in the low 60s the content is present-but-quieted,
which is the point of the opaque variant.

## 3. Saturate up, brightness down

`saturate 135% → 206%`, `brightness 1.1 → 0.96`. The old values *lifted* the
backdrop (brighter, less saturated) which looks like cheap shiny plastic. Apple's
frost is the opposite: it **pulls saturation up and brightness slightly down**, so
colors behind bloom into a soft milky wash instead of a glossy sheen.

## 4. No drop shadow — dim the rest instead

Apple does **not** float the menu on a drop shadow. It grounds it by darkening
*everything else* a few percent. We deleted the two outer `box-shadow` elevation
layers and added a full-screen scrim **beneath** the surface:

```css
.scrim { position: fixed; inset: 0; z-index: 40; pointer-events: none;
         background: rgba(0,0,0, 0.06); }
```

Because the scrim sits *under* the glass, the glass's own `backdrop-filter`
samples the dimmed feed too — the dimming reads as coming *through* the material,
not painted on top. A drop shadow says "this is a card hovering above"; a dim says
"this is a layer the whole UI has deferred to." The latter is the Liquid Glass
hierarchy stance.

## 5. Flat icons + labels, no chip circles

The old dock wrapped each icon in a grey/colored filled circle (a "chip"). Apple
uses **none** — thin-stroke outline glyphs sitting directly on the glass, label
beneath, near-black by default, with color used as a *tint on the icon+label*
(red destructive, blue primary), never as a filled background.

```css
.dock-btn { color: #1d1d1f; }            /* near-black, not slate */
.dock-btn svg { fill: none; stroke: currentColor; stroke-width: 1.7; }
.dock-btn--danger { color: #ef4444; }    /* tint only */
.dock-btn--accent { color: #0ea5e9; }
```

**Lesson:** filled chips add a second material competing with the glass. Stripping
them lets the glass be the only surface and the icons behave like text — which is
exactly how SF Symbols sit in a real menu.

## Final dialed-in knobs

| knob | value |
|---|---|
| white % (gradient peak) | 63 |
| blur | 7px |
| saturate | 206% |
| brightness | 0.96 |
| dim (scrim) | ~6% |

## 6. Icon + type precision (the follow-up pass)

Once the material read as iOS glass, the remaining gap was **iconography and
typography**. Two fixes, no new surface work:

- **Real lucide paths, not hand-rolled SVGs.** The first icons were approximated
  by hand and read as imprecise (uneven optical weight, off proportions). Swapped
  in the exact lucide glyphs the client already ships (`X`, `Check`, `Trash2`,
  `Podcast`, `GitMerge`, `FileText`), drawn on lucide's native 24-grid. Lucide is
  the closest web stand-in for SF Symbols — consistent grid, joins, and caps.
- **Match icon weight to text weight.** Icon stroke went `1.7 → 2` (lucide-native,
  ≈ SF Symbols regular) and the label dropped `500 → 400` (SF Pro regular) with a
  hair of negative tracking. The point: glyph and label should look like one
  family. SF Symbols are tuned to sit at the weight of the text beside them;
  a thin icon next to a semibold label is the tell that breaks the illusion.

**Ceiling reached:** SF Symbols themselves are Apple-proprietary and can't be used
on the web, so lucide + weight-matching is the practical limit. `-apple-system`
already renders the labels in real SF Pro on Apple devices, so the type is genuine;
only the glyphs are a stand-in.
