---
last_updated: 2026-02-17 08:01, c62aa7b
---
# Summary Lifecycle Animations — Visual Spec

The interaction intentionally smells like gaming: charging for a magic attack. Fantasy / anime.

The 500ms charge window is the critical constraint. Most real taps are 100–200ms. The animation must land on a quick tap AND reward a slow one — exactly how game charge mechanics work: a quick tap on a chargeable attack still fires something satisfying, but holding it longer gives a more dramatic release.

## Finger down — border ignition

The card's border instantly lights up with a thin luminous line, originating from the point on the perimeter closest to where the finger touched. Not a fade-in — it's there on the first frame, like flipping a switch. A cool-toned glow (blue-white, or brand color at high luminosity). Simultaneously, a very soft radial gradient appears behind the card content, centered on the touch point, like a dim spotlight turned on beneath the card surface. The card scales down to 0.99 (already happening via `whileTap`).

## Hold — the charge builds

The border glow begins to slowly creep outward from the ignition point along both directions of the perimeter, like a lit fuse branching left and right. It pulsates subtly (~2Hz). The radial spotlight behind the content brightens slightly and widens. The total escalation across the full 500ms is restrained — a candle flame growing steadily, not an explosion building. A 150ms tap gets a flash. A 400ms hold gets a card that's visibly "charged" with the border glow having crept maybe 30–40% around the perimeter.

## Finger up — the circuit completes

This is the payoff. Wherever the border glow had reached, it suddenly accelerates and snaps around the entire card perimeter in ~150ms. Like a fuse reaching the charge: the slow creep becomes an instant circuit completion. At the moment the circuit closes, a single brief flash pulses through the card background (~50ms), then the glow settles into steady-state: a single bright point continuously traveling around the border. The traveling spark IS the loading animation. The transition from "release burst" to "loading line" is seamless because they're the same visual element — the border glow. The release just completes the circuit, and then the bright point keeps running laps.

## Loading — the spark runs laps

A luminous point (or short gradient segment) traveling around the card's border at a steady pace. The rest of the border retains a very faint residual glow — the circuit is "live" but the energy is concentrated in the traveling point. This communicates "working on it" without demanding attention.

## Arrival — the spell lands

When the summary arrives, the traveling point completes its current lap, then the entire border flashes simultaneously (~200ms, all segments glow at once). The overlay opens. The border glow fades.

## The arc

The full arc maps cleanly to the charge-attack pattern:

1. **Touch** → magic circle appears (border ignites from touch point)
2. **Hold** → circle charges (glow creeps along perimeter)
3. **Release** → spell fires (circuit snaps shut, flash)
4. **Casting** → spell traveling (spark runs laps)
5. **Impact** → effect lands (full border flash, overlay opens)

## Implementation-relevant details

The ignition point needs the touch position relative to the card, which `useTouchPhase` can expose as a CSS custom property (the angle from card center to touch point). The border animation itself is a single rotating conic-gradient on a pseudo-element — GPU-composited, no JS per frame, just a CSS animation class toggled by the data attributes.
