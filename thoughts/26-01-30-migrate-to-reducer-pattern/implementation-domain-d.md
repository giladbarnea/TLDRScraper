# Suggestion: Domain D (Gesture / Interaction) reducer technique

## Intent
Domain D is the global interaction layer (`idle` → `dragging` → `select-mode`). This seems like the most timing-sensitive domain, so a reducer technique that makes input handling explicit could keep the rest of the stack predictable.

## Proposed technique (advisory)
Consider modeling gestures as **short-lived sessions** with a small, explicit payload carried through the reducer. That session could hold pointer id, starting coordinates, and a derived `gestureKind` (e.g., `drag` vs `tap-candidate`). The reducer would be the only place that promotes a session into `dragging`, which might reduce ambiguous tap-vs-drag behavior.

### Sketch
**State shape (hypothetical)**
- `mode`: `idle | dragging | select-mode`
- `activeSession`: `{ pointerId, startX, startY, currentX, currentY, gestureKind } | null`
- `dragDelta`: `{ dx, dy } | null` (optional convenience for rendering)

**Events**
- `POINTER_DOWN`
- `POINTER_MOVE`
- `POINTER_UP`
- `POINTER_CANCEL`
- `SELECT_MODE_ENABLED`
- `SELECT_MODE_DISABLED`

**Thresholds**
A small movement threshold (e.g., 6–10px) could decide whether the session upgrades to `dragging`. This might reduce accidental drags and could simplify the “tap ignores drag” logic by making it implicit in the reducer.

### Why this might help
- **Clear promotion rules:** upgrading to `dragging` would be a single explicit transition, which could make it easier to reason about when taps are allowed.
- **Global consistency:** if `select-mode` is global, treating it as a top-level mode might keep input handling uniform across cards.
- **Early returns:** the reducer could short-circuit in `select-mode` and ignore drag paths, which might keep the rest of the UI flow simpler.

## Coordination with Domains B/C (in progress)
If Domains B/C stay orthogonal, Domain D could emit only **outcome events** like `DRAG_STARTED`, `DRAG_COMMITTED`, or `DRAG_ABORTED` without knowing about summaries. That might keep it “closed” while still providing signals for the mediator (if you keep the mediator pattern). The mediator could then decide whether a drag commit should close a summary view or simply mark the lifecycle as removed.

## Potential outcomes (hypothesized)
- **Might reduce gesture race conditions** when a user starts dragging while a summary request is inflight.
- **Could clarify the tap-vs-drag boundary** by making the promotion rule explicit and stateful.
- **May make debugging easier** since all pointer state lives in a single domain and can be logged with state transitions.

## Open questions
- Should `select-mode` lock out all drag transitions, or should it allow a specialized “selection drag” path?
- Do we want the reducer to produce a small `renderPatch` (e.g., `dx`) to keep view code dumb, or keep render calculations inside the hook?

If this direction seems useful, the next step might be to draft a tiny `gestureReducer.js` prototype that only handles pointer tracking and produces `DRAG_*` outcome events for a mediator to consume.
