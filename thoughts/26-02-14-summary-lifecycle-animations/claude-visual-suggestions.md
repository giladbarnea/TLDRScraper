---
last_updated: 2026-02-17 08:01, c62aa7b
---
# Visual Animation Suggestions — Claude

## Design principles

What separates AAA game magic from cheap web effects:

1. **Color restraint.** One color family. Not a palette, not a gradient rainbow. AAA magic reads as *light*, not *color*.
2. **Timing discipline.** Slow build, sharp release. The charge is contemplative; the discharge is instant. Skyrim frost builds in the palm for seconds but fires in one frame.
3. **No particles.** On web, particles always look like a student project. Skip them entirely. The border itself is the effect.
4. **Material honesty.** Glows should feel like actual emitted light — soft falloff, physically plausible radii. Not painted-on opacity overlays.
5. **Single overshoot maximum.** Springs that bounce more than once feel like jelly. One overshoot, then settle.
6. **Content is sacred.** Nothing blurs, dims, or obscures the article title/meta. The animation lives on the card's *edge*, not its *face*.

## Color

**Cool white-blue.** `hsl(210, 60%, 90%)` as the base, pushed to `hsl(210, 80%, 95%)` at peak brightness.

Why this color:
- Reads as "light/energy" rather than "decorative color." Gandalf's staff, Elder Scrolls frost rune, Harry Potter's Lumos — all white with a cold tint.
- Doesn't compete with content or UI chrome.
- Works in light mode without looking washed out, and in dark mode without being garish.
- Luxury and AAA both default to "white with a hint" because it signals purity of intent.

NOT warm gold (too Harry Potter–specific, clashes with info-dense UI). NOT brand color at full saturation (animation should feel like physics, not marketing).

## The border as the sole animation surface

Every phase of the lifecycle animates the card's **border perimeter** only. No internal gradients, no radial spotlights, no content overlays. The border is a thin luminous line (1.5–2px visual weight) that lives on a `::before` pseudo-element with `border-radius` matching the card. This is the "magic circle" — the entire animation vocabulary is: where on the perimeter is lit, how bright, and how fast it moves.

This constraint is what makes it feel precise rather than showy. It's one element, one color, one dimension (the perimeter arc). Like a rune circle in Elder Scrolls — a single glowing line doing all the expressive work.

## Phase 1: Finger down — ignition (PRESSED, t=0)

**Reference feel:** Gandalf's staff hitting stone. The light doesn't fade in — it's there on the first frame.

A short arc of the border (approximately 5% of the total perimeter, ~20px on a typical card) lights up at full brightness, centered on the perimeter point closest to where the finger touched. Instant. No transition. Frame 1 = fully lit segment.

The ignition point requires the touch position relative to the card, which `useTouchPhase` can expose as a CSS custom property: `--touch-angle` (the angle in degrees from card center to touch point). The `::before` element uses a `conic-gradient` starting at that angle, with a sharp transparent-to-lit-to-transparent transition defining the arc width.

Simultaneously:
- `scale(0.985)` via the existing `whileTap` spring. Tactile compression.
- A barely-perceptible `box-shadow` appears: `0 0 8px 0 rgba(190, 210, 255, 0.12)`. Subconscious light spill. Not enough to consciously notice; enough to make the card feel "alive."

Duration of this phase: as long as the finger is held, up to 500ms.

## Phase 2: Hold — the fuse burns (PRESSED, t > 0)

**Reference feel:** Dragon Ball charge-up, but quiet. Energy concentrating, not exploding.

The lit arc begins to grow outward in both directions along the perimeter. Not a smooth CSS transition — it's driven by a CSS animation that starts on the first frame of PRESSED and runs for 500ms. If the finger lifts at any point during those 500ms, the animation is at whatever percentage it reached.

Growth curve: ease-out. Fast at first (the ignition "catches"), then slows down. At 150ms (typical quick tap), approximately 12–15% of perimeter is lit. At 400ms (deliberate hold), approximately 35–40%.

The **leading edge** of each growing arm is brighter than the trail behind it. Implementation: the conic-gradient has a 3-stop structure — dim base → bright head → transparent. The bright head advances; the dim base fills in behind it. Like a fuse: the burning point is bright, the charred trail behind it is a dimmer ember.

No pulsing. Pulses feel cheap. The brightness ramp is monotonic: it only ever increases during this phase. Restraint.

The box-shadow deepens proportionally: from `0.12` opacity to `0.18` over the full 500ms. Barely noticeable unless you're looking for it.

## Phase 3: Finger up — the circuit closes (RELEASED, ~120ms)

**Reference feel:** The moment a Skyrim spell leaves the hands. Or Tekken rage art activation — one frame of compressed power, then the strike.

Whatever percentage of the perimeter was lit, it now accelerates and completes the full circuit in exactly 120ms. The two arms of the fuse race toward each other and meet on the opposite side of the card. The easing is ease-in: starts at the fuse-creep speed, accelerates to a snap.

At the frame the circuit closes (the two arms meet):
- The entire border reaches peak brightness simultaneously for exactly **2 frames** (~33ms at 60fps). This is the "surge" — the circuit completing. Not a flash (flashes are cartoon). A surge: full brightness, held for just long enough to register, then it settles.
- The `box-shadow` sharpens to: `0 0 14px 1px rgba(190, 210, 255, 0.22)`. Brief. Settles back to `0 0 6px 0 rgba(190, 210, 255, 0.10)` over 80ms.
- `scale` returns to `1.0` with a spring that slightly overshoots to `1.003` then settles. ONE overshoot. No bounce.

After the surge, the border settles to a uniform dim glow — the entire perimeter at ~30% of peak brightness. The circuit is closed, current is flowing. This is the steady-state that bridges to Phase 4.

This phase lasts `RELEASE_DURATION_MS` (400ms total, but the visible action is the 120ms snap + 33ms surge + 250ms settle).

## Phase 4: Loading — the spark runs laps (summaryStatus=loading)

**Reference feel:** A rune circle slowly rotating. Or the loading indicator from Destiny 2 — a single bright element orbiting a path. Composed. Not anxious.

The uniform dim glow from Phase 3's settling concentrates into a single bright point over ~300ms. The point is a gradient arc: approximately 8% of the perimeter (bright head, tapered tail). The rest of the border retains a very faint glow (~10% of peak brightness) — the circuit is "live" but the energy is concentrated in the traveling point.

Speed: **one full lap every 2.5 seconds**. This is critical. Too fast (1s) = loading spinner anxiety. Too slow (4s) = feels stuck. 2.5s is the tempo of a slow, confident breath. The rotation is `linear` easing — constant velocity, no acceleration per lap. The consistency itself communicates "working, not struggling."

Implementation: a `conic-gradient` on `::before`, animated via `@keyframes rotate { to { --border-angle: 360deg; } }` using `@property` registered custom property for GPU-composited rotation. Alternatively, `rotate` on the pseudo-element itself if the gradient is pre-defined. No JS per frame.

The transition from Phase 3 (full border glow) → Phase 4 (traveling spark) is: the brightness differential appears gradually. The full glow doesn't "switch off" — the bright region just becomes more concentrated as it starts to move. 300ms for this condensation. The effect is that the energy is "gathering itself" into the traveling spark.

## Phase 5: Arrival — spell lands (summaryStatus → available)

**Reference feel:** A spell impacting its target in LOTR. A single expanding ring of light, then stillness.

The traveling spark **accelerates** during its final half-lap — speed doubles over 1.25s (ease-in). This creates anticipation: the spark is completing its work.

When the spark completes the lap (returns to its origin), the entire border simultaneously reaches peak brightness for **100ms** (longer than the 33ms surge in Phase 3 — this is the finale, it deserves a beat). A single, confident pulse. Not repeating. Just: bright → done.

Then the border fades entirely over 400ms (opacity 1 → 0). The overlay is already beginning to open during this fade. The border completing its business and fading out feels like a spell dissipating after impact — the energy has been transferred to the result (the overlay).

No additional effects at arrival. The overlay opening IS the impact. The border fading is the follow-through.

## Timing diagram

```
t=0ms      pointerDown    border ignites at touch point (~5% perimeter arc)
                          scale(0.985), faint box-shadow
t=0–500ms  holding        fuse burns outward (ease-out), up to ~40% at 500ms
                          leading edge bright, trail dimmer
t~150ms    pointerUp      circuit-close begins (120ms, ease-in)
t~270ms    circuit closed  2-frame surge (33ms), entire border at peak
                          scale overshoots to 1.003, settles to 1.0
t~270ms    settle          border settles to uniform dim glow (~250ms)
t~270ms    loading starts  energy condenses into traveling spark (300ms)
t~570ms    spark running   one lap / 2.5s, linear, constant velocity
  ...      server work     spark runs steady laps
t~5-30s    response        spark accelerates final half-lap (speed 2x)
           lap completes   full border flash (100ms)
           overlay opens   border fades out (400ms)
```

## Implementation architecture

All animation lives in CSS. The data attributes already on the DOM (`data-touch-phase`, `data-summary-status`) are the only interface. No additional JS animation logic needed.

```
Card ::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  background: conic-gradient(from var(--border-angle, 0deg), ...);
  mask: /* border-only mask: outer radius minus inner radius */;
  opacity: 0;
  transition: opacity 300ms;
}

[data-touch-phase="pressed"] ::before   { opacity: 1; animation: fuse-burn 500ms ease-out forwards; }
[data-touch-phase="released"] ::before  { opacity: 1; animation: circuit-close 120ms ease-in forwards; }
[data-summary-status="loading"] ::before { opacity: 1; animation: spark-orbit 2.5s linear infinite; }
```

The `--touch-angle` custom property (set by JS on pointerDown) determines the conic-gradient's starting point. This is the only JS→CSS bridge per interaction.

`@property --border-angle` registered as `<angle>` enables GPU-composited animation of the gradient rotation.

## What this intentionally excludes

- **No inner card effects.** No gradients, spotlights, or background color shifts on the card face. The border does all the work.
- **No particles.** Zero.
- **No blur/glow on content.** Title and meta text are never touched.
- **No shake or vibrate.** That's mobile game notification territory.
- **No multi-color.** Single color family throughout. The intensity varies; the hue does not.
- **No sound.** Obviously.

## The arc, restated

Ignition → Fuse → Surge → Orbit → Flash → Fade.

One visual element (the border). One color (white-blue). Five intensities across six moments. That's it.
