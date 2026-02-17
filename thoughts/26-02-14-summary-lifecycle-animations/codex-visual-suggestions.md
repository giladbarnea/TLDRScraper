---
last_updated: 2026-02-17 08:01, c62aa7b
---
# Codex Visual Suggestions — Summary Lifecycle Animations

These suggestions assume the technical layer is already exposing:
- `data-touch-phase="idle|pressed|released"`
- `data-summary-status="unknown|loading|available|error"`

The visual goal is **AAA “arcane power”**: crisp, precise, material-aware, and restrained. Think “Elder Scrolls mage UI” / “LotR elven craft” more than neon cyberpunk, and “Tekken / DBZ charge” more than cartoon sparkles.

---

## Global art direction (so everything feels like one system)

### 1) One metaphor: **arcane circuit**
The card becomes a “rune-etched plate” that, when touched, closes an arcane circuit around its perimeter.
- **Touch**: the circuit **ignites** at a point.
- **Hold**: the circuit **charges** (energy propagates).
- **Release**: the circuit **snaps closed** (discharge impulse).
- **Loading**: the circuit runs a **single traveling spark** (steady work).
- **Success**: the circuit **flashes full** once (impact), then yields to “available”.

This keeps continuity: the same border language carries the whole lifecycle.

### 2) Material + thickness
Avoid thick “gamey” borders. The AAA look is *thin line work with convincing light*:
- Primary stroke: **1px** luminous filament (reads as precision).
- Secondary halo: **2–6px** soft bloom (very low opacity).
- Background energy: a **very subtle** inner wash (radial), not a full card tint.

### 3) Color discipline (don’t go rainbow)
Pick **one** main element color and stick to it.
- Recommended: **brand sky** (existing design system) as the energy hue.
- Structure:
  - **Core**: near-white / pale ice
  - **Body**: brand hue
  - **Halo**: brand hue at low alpha
  - Optional “impact” accent (only on success): **warm pale gold** *at very low intensity* (reads like “spell landed” without changing the brand).

### 4) Motion rules
Polish comes from consistent timing and easing:
- **Ignition**: immediate (first frame), then a *micro settle* (80–120ms).
- **Charge ramp**: linear-ish propagation, *not* a bounce.
- **Release**: fast, clean, no overshoot (feel like a circuit completing, not a blob).
- **Loading**: steady pace (calm competence).

Avoid cartoon “boing” easings. Prefer: `easeOutCubic`, `easeOutExpo` for quick snaps; `linear` for loops; `easeInOutSine` for subtle pulsing.

---

## Per-state visual suggestions (what the user should feel)

### A) `idle + unknown` (default)
No magic. The card should look *quiet and trustworthy* so the magic stands out.
- Border: neutral (existing).
- No background wash.
- Summary affordance: none (or minimal).

### B) `pressed + unknown` (finger down: “ignite”)
**First-frame feedback** is mandatory; the touch must feel “powered”.

**Border ignition**
- A thin luminous segment appears on the perimeter at the closest edge to the touch point (as in `visual-spec.md`).
- The segment is short (think 8–18px of perimeter length), crisp, and bright.
- Add a tiny “hot core” bead (1–2px) that implies energy has a leading point.

**Internal response**
- A very soft radial wash appears under content, centered on touch point:
  - Extremely subtle (barely lifts the local contrast).
  - Should never reduce text legibility.

**Micro-audio vibe without audio**
- Add a single-frame “specular catch” on the border segment (like a sword edge catching light). This reads premium without needing particles.

**Timing**
- 0ms: on.
- 80–120ms: settle from “too bright” to “steady bright” (a quick damp).

### C) `pressed + unknown` (held: “charge builds” over 0–500ms)
The user must feel escalating potential even on a 150–200ms tap, but holding to ~450ms should visibly reward.

**Propagation**
- The luminous filament creeps along the perimeter in both directions from the ignition point.
- Recommended target by ~400ms: 30–45% of the perimeter “charged”.

**Pulse**
- A restrained pulse at ~2Hz:
  - Prefer *amplitude modulation* (brightness) over size modulation.
  - Keep it subtle; it should read like “energy pressure”, not blinking.

**Background wash**
- Expand the radial wash slightly with time; do not flood the entire card.
- Keep the center brightening modest (think “candle flame grows”, as spec says).

**What NOT to do**
- Don’t emit lots of sparks.
- Don’t wobble the card or shake text.
- Don’t apply a heavy blur; bloom should be barely noticeable.

### D) `released + unknown` (finger up: “circuit completes”)
This is the “power” moment. It needs a decisive snap, not a fireworks show.

**Snap completion**
- The charged perimeter instantly completes: the leading bead accelerates and runs the remaining perimeter in ~120–180ms.
- When it closes the loop, do a single “impact”:
  - Border: brief full-perimeter flash (50–90ms).
  - Card interior: a *very brief* low-alpha wash pulse (one frame + fade), like energy passing through the plate.

**Afterglow**
- Immediately after the snap, transition into the loading mode if the request begins:
  - If summary status switches to `loading` while still in `released` (the overlap window), the same leading bead becomes the loading spark seamlessly.

**Duration alignment**
- Your technical `RELEASE_DURATION_MS` is ~400ms; visually:
  - 0–180ms: snap + impact.
  - 180–400ms: decay into either (a) `loading` loop, or (b) neutral if no fetch happens (e.g., selection latch / suppressed click).

### E) `idle + loading` (in flight: “spark runs laps”)
This should communicate work without shouting.

**Traveling spark**
- A single bright bead (or very short streak) travels around the perimeter:
  - Bead core: tiny, bright.
  - Tail: short gradient (8–24px), fading quickly.
  - Optional: an ultra-faint residual “charged border” behind it (very low alpha).

**Speed**
- Choose a speed that feels deliberate:
  - Roughly 1.2–1.8s per full lap.
  - Keep constant speed (linear) so it feels “engine-like” rather than “toy”.

**Stability**
- No jitter.
- No random particle spawns.
- No direction changes.

**Optional premium touch (still restrained)**
- A faint secondary “phase” glimmer that appears only when the bead crosses corners (rounded corners get a tiny specular tick). This makes the geometry feel real.

### F) `idle + available` (cached summary: “enchanted / ready”)
This is where most designs look either too subtle or too loud. The best compromise:

**Make it readable at scan distance, but static**
- Use a semantic indicator that’s clearly not chrome:
  - Preferred: a small **“TLDR”** label or badge (text + color) rather than only an icon.
  - Color: brand hue (or a restrained emerald if that’s the established semantic success color elsewhere), but do not glow like loading.

**Optional micro-glow**
- If you want a hint of enchantment, keep it *static*:
  - A 1px inner border tint (very low alpha) or a subtle corner glint.
  - No looping animation in `available` state (looping should belong to `loading` only).

**On touch (pressed/released while available)**
- Reuse the ignition/snap logic, but reduce intensity:
  - It should feel like “opening a charged item” rather than “casting a spell”.
  - The release snap can be shorter (80–120ms) since there’s no network wait.

### G) `idle + error` (failed: “miscast / fizzled”)
Error should feel like a controlled failure, not alarm UI.

**Miscast**
- The traveling spark slows and “snuffs”:
  - Spark dims, tail shortens, then disappears.
  - Border returns to neutral with a faint “scorch” tint (optional) that fades quickly.

**Color**
- Keep error hue subdued (avoid bright red neon).
- Use existing design system error semantics, but keep motion minimal.

**Do not**
- Flash red repeatedly.
- Shake the card.

---

## Cancellation paths (polish comes from how you stop)

### Scroll cancellation (`pressed → idle` via move threshold)
The moment the user scrolls, the magic must *respect the scroll* and vanish gracefully.
- Border filament collapses quickly (60–120ms fade).
- Radial wash retracts (fade + slight shrink).
- No release snap (because no `released` phase).

### Long press to select (`pressed → idle` at 500ms)
This is a “mode switch” and should not look like a bug.
- At ~500ms when auto-cancel fires:
  - Border filament dissipates into the corners (a subtle “wick” fade) or simply fades out quickly.
  - Avoid any discharge flash (no `released`).
- If selection checkmark appears, ensure it visually wins over the magic (magic should be gone first or simultaneously).

---

## Overlay opening / continuity (available → expanded)
The visual arc should connect the card to the full-screen overlay.

**Recommended continuity move**
- On success (summary arrives) and right before overlay opens:
  - The border does one full-perimeter “impact” flash (140–220ms).
  - The internal wash expands slightly (like the card is “opening”) then hands off to overlay mount.

**Avoid**
- Crossfades that feel like a different UI layer.
- Big zooms (can feel cheap unless perfectly tuned).

---

## “AAA” don’ts checklist (prevents cheapness)
- Don’t use thick glowing outlines.
- Don’t use random spark particle spam.
- Don’t use elastic/bouncy easing on “magic”.
- Don’t animate text color/position; keep content stable.
- Don’t do multi-layer simultaneous loops (one loop max: the loading spark).
- Don’t strobe: keep pulses under ~3Hz and low amplitude.

---

## Accessibility / motion comfort
Even for power users, the UI must stay readable.
- Respect `prefers-reduced-motion`: no perimeter travel; replace with a static “charged border” and a subtle opacity pulse (or none).
- Maintain contrast: background washes must not reduce text contrast.
- Avoid bright flashes: the success “impact” should be brief and controlled.

---

## Quick “north star” sequence (what it should feel like)
1) Touch: *“I touched an enchanted plate.”* (instant filament + soft inner glow)
2) Hold: *“Power is building.”* (perimeter propagation + restrained pulse)
3) Release: *“Spell fired.”* (snap completion + single impulse)
4) Loading: *“Work in progress.”* (one calm spark lapping the border)
5) Success: *“Impact landed.”* (one full flash, then ready state)
6) Available: *“Ready.”* (static badge/semantic color, no loops)

