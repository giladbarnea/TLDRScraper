---
last_updated: 2026-02-17 08:01, c62aa7b
---
# Summary Lifecycle Animations

## Problem

Two article card states are poorly designed and misaligned with the app's design philosophy:
**summary loading** (spinner) and **summary available** (down-arrow icon).

Both states express themselves through a single axis of differentiation — swapping a 14px icon in the meta row. This violates the UI_DESIGN principle that each level must differ from its neighbors in at least two properties.

### Loading state — current

The entire feedback for "I'm fetching your summary" is a 14px `Loader2` spinner in the meta row, colored `brand-500`. Problems:

- **Only one axis of differentiation.** The card looks identical to its resting state except for a tiny icon swap.
- **No structural acknowledgment of user intent.** The user tapped the card to request a summary — a committed action with a multi-second wait. The card's boundary (border, shadow, background) doesn't change. No sense the card has entered a different mode.
- **No visual bridge to zen overlay.** The progression default → loading → expanded is discontinuous. The card is static until suddenly a full-screen overlay appears.

### Summary available state — current

The only indicator that a cached summary exists is an `ArrowDownCircle` at `slate-300` — the chrome level. Problems:

- `slate-300` is for elements "present if you look for them, invisible if you don't." Wrong for actionable state.
- Having a cached summary is **actionable** — "tap to read the TLDR." Treating it as chrome buries it.
- The architecture doc says "Cached summaries show 'Available' (green)" but the implementation reduces this to a muted icon indistinguishable from read checkmarks at scanning distance.

---

## Design direction: loading

The summary is AI-generated. It's not "loading content" like downloading a file. It's a magical process — novel enough in 2026 to be a dopamine spike alongside the usual mild user impatience with waiting. The balance between "magic at your fingertips" and "yet you're waiting" lives in micro-interactions.

### The three-phase touch interaction (git metaphor)

The touch lifecycle maps to three distinct animation phases:

1. **Finger down — "git add"**
   A magical animation triggers on touch-start, communicating: *"you have just tapped/stirred a magical item and the magic is a live, reactive thing."* The card acknowledges the touch immediately with a visual spark.

2. **Finger held — "git commit"**
   While the finger is held, a continuous animation communicates: *"card is subtly magically agitated."* The card is charged, alive, responding to the sustained touch.

3. **Finger up — "git push"**
   On touch-end, triggers an animation that communicates: *"magic process just fired."* Only on finger-up does the summary request actually fire. This is the moment of release — the energy built up in phases 1-2 is dispatched.

### Phase 4: loading in progress — "magic line"

Once the request is in flight, the card needs movement at the card level. Idea: a "magic line" that traces the card's border — not too quickly — circling continuously while the summary is being generated. This gives the card structural framing (border animation) that differs from resting state on two axes: border treatment + icon.

### Continuity principle

The full visual progression should feel like a ramp:
**default card → touch-charged card → loading card → available card → expanded zen overlay**

Each step should look like an intermediate point in a continuous sequence, not discrete jumps.

---

## Design direction: summary available

The available state should use semantic color, not chrome color.

Options under consideration:
- A small **"TLDR" badge** in the meta row (`text-xs font-medium text-brand-500` or `text-emerald-500`) replacing the arrow icon. Two axes of differentiation: text + color.
- Keep the icon but shift to `text-brand-400` or `text-emerald-400` — lighter touch but possibly insufficient alone.
- Card border/shadow subtly differs for articles with summaries.

---

## Implementation strategy

These are two separate workstreams that should be tackled one at a time:

1. **Technical aspect** — the touch interaction model (finger-down / held / up lifecycle), request timing (fire on finger-up), gesture detection, state machine for the three phases + loading + available.

2. **Visual aspect** — the actual animations, colors, border treatments, transitions. CSS keyframes, Tailwind utilities, the "magic line" border animation, the touch-phase visual feedback.

Order: technical first, visual second. The technical layer defines what states and transitions exist; the visual layer skins them.

---

## Status

### Technical aspect: COMPLETE (2026-02-15)

The touch phase state machine is fully implemented and verified on device:

- **`useTouchPhase` hook** — tracks `idle → pressed → released → idle` lifecycle via pointer events
- **`touchPhaseReducer`** — pure reducer for state transitions, guards all impossible edges
- **`interactionConstants.js`** — shared thresholds (`LONG_PRESS_THRESHOLD_MS=500`, `POINTER_MOVE_THRESHOLD_PX=10`, `RELEASE_DURATION_MS=400`)
- **`data-touch-phase` and `data-summary-status`** — exposed as DOM data attributes on the card surface for CSS targeting
- **Transition logging** — all phase transitions logged to quake console via `logTransition`
- **Selectable coexistence** — pointer handlers on the card's `motion.div` coexist with Selectable's long-press handlers on the outer wrapper; no `stopPropagation` conflicts

#### Key debugging findings

1. **Selectable wrapper was initially blocking pointer events.** `useLongPress` in Selectable sets `touch-action: manipulation` and attaches `pointerdown`/`pointermove`/`pointerup` listeners on its own wrapper div. Early hypothesis: these might intercept events before the inner card. Verified this was NOT the issue — both layers fire independently.

2. **AUTO_CANCEL timing is the gatekeeper for RELEASED.** The 500ms auto-cancel timer in `useTouchPhase` runs in parallel with Selectable's 500ms long-press timer. For taps shorter than 500ms (typical: 100-400ms), the lifecycle completes normally: `idle → pressed → released → idle`. For holds longer than 500ms, AUTO_CANCEL fires, clears the pointer tracking (`reset()`), and subsequent `pointerUp` is a no-op — `RELEASED` never occurs. This is correct behavior: long holds enter selection mode, not summary mode.

3. **Verified end-to-end on device (2026-02-15 09:36):**
   ```
   pointerDown → id=-2035765572 type=touch
   idle → pressed
   pointerUp → id=-2035765572 (tracked=-2035765572)   ← pointer still tracked (tap < 500ms)
   pressed → released
   click: summary.toggle() fires
   released → idle                                      ← RELEASE_DURATION_MS timer
   summary: unknown → loading → available
   summary-view: collapsed → expanded
   ```

### Visual aspect: IN PROGRESS

Now that the technical state machine is proven, the visual layer can target the data attributes. See `visual-spec.md` for the design direction.
