---
last_updated: 2026-04-09 09:14, 81662be
---
# Interaction & Selection Domain: Code Smells & Opportunities

**Date**: 2026-04-08
**Scope**: InteractionContext.jsx, interactionReducer.js, interactionConstants.js, useLongPress.js, Selectable.jsx, SelectionActionDock.jsx, SelectionCounterPill.jsx

---

## Summary

The Interaction & Selection domain implements a selection state machine with long-press activation, container-level selection, and expand/fold coordination. The architecture is generally sound, but there are several clear opportunities for simplification and deduplication.

---

## High-Value Findings

### 1. Duplicated Pattern: `descendantIds` Computation (3 locations)

**Files**: `CalendarDay.jsx:30-31`, `NewsletterDay.jsx:67-68`, `NewsletterDay.jsx:32-33`

The same pattern appears in three places:

```javascript
const componentId = `calendar-${date}`  // or newsletter-..., or section-...
const descendantIds = articles.map(a => `article-${a.url}`)
```

**Impact**: Every new container type must remember to compute both IDs. If the `article-` prefix changes, it must change in multiple places.

**Opportunity**: Extract to a utility function, or derive `descendantIds` automatically from children at the `Selectable` level.

---

### 2. Double-Dispatch Pattern in InteractionContext

**File**: `InteractionContext.jsx:45-49` and `InteractionContext.jsx:39-44`

The `dispatchWithDecision` function calls `interactionReduce` to get the result, then dispatches a `REPLACE_STATE` event. But `reducerWrapper` also calls `interactionReduce` for non-REPLACE_STATE events:

```javascript
// dispatchWithDecision calls interactionReduce first
const result = interactionReduce(state, event)
rawDispatch({ type: INTERNAL.REPLACE_STATE, nextState: result.state })

// But reducerWrapper ALSO has interactionReduce for the normal path
const reducerWrapper = useCallback((currentState, event) => {
  if (event?.type === INTERNAL.REPLACE_STATE) {
    return event.nextState  // Short-circuit here
  }
  return interactionReduce(currentState, event).state  // Redundant for dispatchWithDecision path
}, [])
```

**Impact**: Cognitive overhead. Two dispatch paths exist (via `dispatchWithDecision` vs direct `rawDispatch`), each triggering different code paths in the reducer wrapper.

**Opportunity**: Either:
- Remove the decision pattern entirely and return decisions through a separate mechanism
- Make all dispatches go through a single unified path

---

### 3. Redundant Wrapper Div in Selectable

**File**: `Selectable.jsx:24-26`

```javascript
<div ...>  {/* Outer div with handlers */}
  <div>    {/* This inner div serves no purpose */}
    {children}
  </div>
  {selected && (...)}
</div>
```

**Impact**: Unnecessary DOM depth.

**Opportunity**: Remove the inner `<div>` wrapper.

---

### 4. ID Construction Scattered Across Components

**Files**: 
- `ArticleCard.jsx:64`: `article-${article.url}`
- `CalendarDay.jsx:29`: `calendar-${date}`
- `NewsletterDay.jsx:65`: `newsletter-${date}-${issue.source_id}`
- `NewsletterDay.jsx:31`: `section-${date}-${sourceId}-${sectionKey}`

**Impact**: No single source of truth for ID construction. The `descendantIds` in parent containers must match the IDs constructed in children.

**Opportunity**: Centralize ID construction functions:
```javascript
// lib/selectionIds.js
export const articleId = (url) => `article-${url}`
export const calendarId = (date) => `calendar-${date}`
export const newsletterId = (date, sourceId) => `newsletter-${date}-${sourceId}`
export const sectionId = (date, sourceId, sectionKey) => `section-${date}-${sourceId}-${sectionKey}`
```

---

## Medium-Value Findings

### 5. Underutilized `didLongPressRef` from useLongPress

**File**: `useLongPress.js:65`

```javascript
return {
  handlers: { ... },
  didLongPressRef,  // Never used by Selectable
}
```

The `Selectable` component never uses `didLongPressRef`. This is either dead code or an incomplete feature.

**Opportunity**: Either remove `didLongPressRef` from the return value, or document its intended use.

---

### 6. Selection Visual Coupled with Gesture Detection

**File**: `Selectable.jsx`

`Selectable` handles:
1. Long-press gesture detection (via `useLongPress`)
2. Selection visual indicator (checkmark overlay)
3. Event propagation (`stopPropagation`)

**Impact**: The selection indicator is tightly coupled with the gesture mechanism. If you wanted a different selection indicator style or position, you'd need to modify `Selectable`.

**Opportunity**: Extract the visual indicator to a separate `SelectionIndicator` component that `Selectable` composes.

---

### 7. Decision Pattern Underutilized in Reducer

**File**: `interactionReducer.js:165-170`

The reducer returns `{ state, decision }` but `decision` is only non-null for `ITEM_SHORT_PRESS`. All other event types return `{ state, decision: null }`.

**Impact**: The decision pattern adds complexity (the double-dispatch mentioned in #2) for a single use case.

**Opportunity**: If decisions are only needed for `ITEM_SHORT_PRESS`, handle that case specially in the context rather than burdening every event type with the decision pattern.

---

### 8. Duplicate ID Passed to Selectable + FoldableContainer

**Files**: `CalendarDay.jsx:33-35`, `NewsletterDay.jsx:69-71`

```javascript
<Selectable id={componentId} descendantIds={descendantIds}>
  <FoldableContainer id={componentId} ...>
```

Both components receive the same `id` string. This is semantically confusing:
- `Selectable` uses the ID for selection tracking
- `FoldableContainer` uses the ID for expand state

**Impact**: The same string serves two conceptually different state concerns. If one changes, the other must change too.

**Opportunity**: Document this coupling clearly, or consider whether the expand state belongs in a different key space than selection state.

---

## Low-Value Findings

### 9. Inconsistent Context Function Return Values

**File**: `InteractionContext.jsx`

Only `itemShortPress` returns a value (`boolean`). All other context functions (`itemLongPress`, `containerShortPress`, `containerLongPress`) return `undefined`.

**Impact**: Minor inconsistency in the API surface.

**Opportunity**: Document the return semantics, or make all functions return a value (even if just `void`).

---

### 10. Suppress Latch Complexity

**File**: `interactionReducer.js:28-35`, `interactionReducer.js:37-41`

The `suppressNextShortPress` latch exists to prevent short-press from firing after a long-press on the same element. It involves:
- State mutation in the reducer
- Time-based expiration (`nowMs()`)
- ID-specific targeting

**Impact**: Global state complexity for a local gesture concern.

**Opportunity**: Consider handling this at the `useLongPress` hook level instead of in global state. The hook could suppress the subsequent `pointerup` directly.

---

## Positive Observations

- **Clean separation**: The reducer is a pure function with no side effects.
- **Well-named events**: `InteractionEventType` enum is clear and exhaustive.
- **Good test surface**: The reducer's pure nature makes it easily testable.
- **Single source of truth**: `InteractionContext` is the sole owner of selection and expand state.

---

## Recommended Priority

1. **#4 (Centralize ID construction)** — Highest impact, lowest effort. Would immediately reduce duplication and coupling.
2. **#1 (DescendantIds computation)** — Goes hand-in-hand with #4.
3. **#2 (Double-dispatch pattern)** — Would simplify the reducer wrapper.
4. **#7 (Decision pattern)** — Related to #2, would further simplify.
5. **#3 (Redundant div)** — Quick cleanup.
6. **#6 (Visual coupling)** — Medium effort, nice-to-have.
