# Implementation: Domain D - Gesture reducer migration

## Scope
Refactor swipe-to-remove gesture handling into a closed reducer and keep select-mode logic in the Interaction domain.

## Decisions (for)
- Added a dedicated gesture reducer to own `idle`/`dragging` transitions and drag error state, matching the reducer pattern used in other domains.
- Centralized swipe completion decisions in the reducer so the hook only executes effects (animations, removal callbacks).
- Kept gesture logging tied to reducer transitions to make state changes explicit.

## Decisions (against)
- Did not add a pointer session model or tap-vs-drag promotion threshold because Framer Motion already gates `onDragStart` and the current UX does not depend on low-level pointer tracking.
- Did not merge select-mode into the gesture reducer because selection state is already owned globally by `InteractionContext`, and duplicating that state would increase coupling.
- Avoided adding new cross-domain mediator logic; the reducer emits a single decision used locally by the hook.

## Result
Gesture behavior now has a closed, testable reducer while keeping the existing interaction and selection architecture intact.
