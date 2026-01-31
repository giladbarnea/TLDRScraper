---
last_updated: 2026-01-30 15:12, 46f9c07
---
# Discussion: Cross-domain (cross state-machine) Reducer pattern state management

# Migrating Client-Side State: From Spaghetti to State Machines

This guide addresses a common scaling problem in frontend development: **Implicit Distributed State.**

As components grow, logic often fragments across multiple `useState` hooks, custom hooks, and event handlers. What begins as "simple booleans" evolves into a complex web of implicit dependencies that are impossible to reason about end-to-end.

This document outlines the move to **Reducer Patterns** and **Finite State Machines (FSMs)**—not just as a code style, but as an architectural necessity for robust interactions.

---

## 1. The Diagnosis: Distributed Implicit State

The most common symptom of a fragile UI is when the behavior of a component is determined by the intersection of multiple independent variables scattered across the file.

### The "ArticleCard" Scenario
Consider a rich UI component like an Article Card with the following features:
* **Tap** to expand a TLDR summary.
* **Swipe** to remove the card.
* **Long-press** for a "Zen Mode" overlay.
* **Async** loading states for the summary.

**The "Spaghetti" Implementation:**
Logic is typically distributed across ad-hoc hooks:
* `ArticleCard.jsx`: Manages `handleCardClick` and `isZenMode`.
* `useSummary`: Manages `loading`, `error`, `expanded`, `html`.
* `useSwipeToRemove`: Manages `dragState`, `dx`, `velocity`.
* `useArticleState`: Manages `isRead`, `isRemoved`.

### The Problem: Combinatorial Explosion
Because these hooks don't talk to each other, you get impossible states and race conditions:
* *Can I swipe while the TLDR is loading?*
* *What happens if `isRemoved` becomes true while `isZenMode` is open?*
* *Does tapping the card toggle the TLDR or close the Zen overlay?*

You end up writing "glue code" full of guard clauses:
```javascript
// The "Glue" Anti-Pattern
const handleTap = () => {
  if (isSwiping) return; // Guard 1
  if (isLoading) return; // Guard 2
  if (isZenMode) {
     closeZen();
  } else {
     toggleTLDR();
  }
};
```
This is fragile. We need a **Single Source of Truth**.

---

## 2. The Solution: The Reducer Pattern

A reducer acts as a transactional engine for your state. It consolidates logic into three core principles.

### Principle A: Single Source of Truth
Merge scattered booleans into a unified state object.

| Distributed (Before) | Unified (After) |
| :--- | :--- |
| `useState(false)` // isSwiping | `state.mode = 'DRAGGING'` |
| `useState(true)` // isLoading | `state.tldr.status = 'LOADING'` |
| `useState(false)` // isZen | `state.mode = 'ZEN'` |

### Principle B: Events, Not Setters (Intent vs. Implementation)
Components shouldn't command *changes* (`setZenMode(true)`); they should announce *events* (`CARD_LONG_PRESSED`). The reducer decides the outcome.

* **Imperative (Bad):** `onClick={() => { if (!loading) setExpanded(true); }}`
* **Declarative (Good):** `onClick={() => dispatch({ type: 'CARD_TAPPED' })}`

### Principle C: Hierarchical Modes (Finite States)
Define high-level **Modes** that dictate which inputs are valid.

* **Mode:** `IDLE` → Accepts `TAP`, `SWIPE_START`.
* **Mode:** `FETCHING` → Ignores `SWIPE_START`.
* **Mode:** `DRAGGING` → Ignores `TAP`.

This eliminates the need for manual guard clauses (`if (!isSwiping)`). The state machine structure *is* the guard.

---

## 3. Architecture Strategies: How to Organize

When migrating, you generally choose between high-level architectures.

### Strategy 1: The Monolith (Master Reducer)
One giant reducer handles everything (Swipe, Fetch, View, Persistence).

* **Pros:** Strict consistency. Easy to enforce rules like "No fetching while swiping."
* **Cons:** Can become a massive file. Hard to reuse parts.
* **Best For:** Highly coupled interactions where every state affects every other state.

### Strategy 2: Orthogonal Domains (Parallel Machines)
Break the state into independent "Domains" running side-by-side.

#### The Domains
1.  **View Domain:** `collapsed` ↔ `expanded` ↔ `zen`
2.  **Swipe Domain:** `idle` ↔ `dragging` ↔ `committed`
3.  **Data Domain:** `idle` ↔ `loading` ↔ `ready`

#### Coordination Patterns
To make these domains work together without coupling, we use specific patterns.

**A. The "Event Broadcasting" Pattern:**
You send the same `event` to *all* machines.

```javascript
function rootReducer(state, event) {
  return {
    view: viewReducer(state.view, event),
    swipe: swipeReducer(state.swipe, event),
    data: dataReducer(state.data, event),
  };
}
```
* If `event` is `SWIPE_START`: `swipeReducer` reacts; `viewReducer` ignores it.

**B. The "Mediator" (Orchestrator) Pattern:**
A separate logic layer listens to Domain A and translates signals for Domain B.
* **Crucial Rule:** The Mediator must listen to **Outcomes** (state transitions), not **Inputs** (user actions).
* **The Flow:** User taps card (`TAP`) → View Reducer accepts it and expands (`VIEW_EXPANDED`) → Mediator hears expansion and commands data fetch (`FETCH_DATA`).

```javascript
// 1. View Reducer handles the INPUT (TAP)
function viewReducer(state, event) {
  if (event.type === 'TAP' && state.mode === 'COLLAPSED') {
    return {
      state: { mode: 'EXPANDED' },
      // Emits the OUTCOME, not the command
      events: [{ type: 'VIEW_EXPANDED', articleId: state.id }]
    };
  }
}

// 2. Mediator handles the COORDINATION
function mediator(event) {
  // Translates "What happened" into "What to do next"
  if (event.type === 'VIEW_EXPANDED') {
    dispatchToData({ type: 'FETCH_DATA', id: event.articleId });
  }
}
```

#### Trade-off Analysis

| Feature | Monolith | Parallel Domains | Mediator |
| :--- | :--- | :--- | :--- |
| **Coupling** | High | Low | Lowest |
| **Reusability** | Low | High | High |
| **Boilerplate** | Medium | Low | High (Bureaucracy) |

---

## 4. The Integration Layer: The Command Pattern

How do pure reducers handle side effects (API calls, Navigation)?
**Answer:** They don't. They return **Commands**.

Instead of `(State, Event) => State`, the signature becomes:
`(State, Event) => { state, commands[] }`

### Example: Expanding an Article
```javascript
function viewReducer(state, event) {
  if (event.type === 'CARD_TAPPED' && state.mode === 'COLLAPSED') {
    return {
      state: { ...state, mode: 'EXPANDED' },
      // The reducer *requests* the effect, it doesn't execute it.
      commands: [{ type: 'ENSURE_TLDR_DATA', articleId: state.id }]
    };
  }
  return { state, commands: [] };
}
```

### The "Runtime" (The Controller)
Since the reducer is pure, it cannot execute the command. You need a "Runtime" (often a custom hook) to act as the bridge between the **Pure World** (Reducer) and the **Impure World** (Browser/Network).

```javascript
function useArticleController(initialState) {
  const [state, setState] = useState(initialState);

  // The Dispatcher acts as the engine
  const dispatch = useCallback((event) => {
    setState((curr) => {
      // 1. Calculate Next State
      const { state: next, commands } = viewReducer(curr, event);

      // 2. Execute Side Effects (The Impure part)
      commands.forEach(cmd => {
        if (cmd.type === 'ENSURE_TLDR_DATA') {
           fetchSummary(cmd.articleId)
             .then(data => dispatch({ type: 'LOAD_SUCCESS', data }));
        }
      });

      return next;
    });
  }, []);

  return [state, dispatch];
}
```

---

## 5. The Migration Playbook

Don't rewrite the whole app. Follow this incremental path.

### Step 1: Pick an Isolated Domain
Start with **Swipe**. It has clear inputs (pointer events) and clear outputs (transform, opacity). It barely touches the rest of the app.

### Step 2: Enforce the "Closed Reducer" Constraint
This is the Golden Rule of migration. To ensure your new reducer works with *any* future architecture, it must be **Closed**.

**The Rules of a Closed Reducer:**
1.  **No Cross-Reads:** It must not read state from other domains (`if (appState.isZen) ...` is forbidden).
2.  **No Direct Effects:** It must not call `fetch()` or `window.scrollTo()`.
3.  **No Hidden Inputs:** It relies *only* on its `state` argument and `event` payload.

### Step 3: Define Stable Event Boundaries
Avoid imperative methods. Define events that describe *what happened*, not *what to do*.

* ❌ `openZenMode()` (Coupled to implementation)
* ✅ `dispatch({ type: 'ZEN_OPEN_REQUESTED' })` (Decoupled intent)

### Step 4: Mechanical Orchestration
Once you have multiple reducers (e.g., View and Swipe), compose them.

```javascript
// The "Dumb" Coordinator
const [state, dispatch] = useReducer((state, event) => {
  // 1. Run Logic
  const nextView = viewReducer(state.view, event);
  const nextSwipe = swipeReducer(state.swipe, event);

  // 2. Collect Commands
  const allCommands = [...nextView.commands, ...nextSwipe.commands];

  // 3. Execute Side Effects (outside the reducer!)
  executeCommands(allCommands);

  return { view: nextView.state, swipe: nextSwipe.state };
});
```

---

## 6. Summary Checklist

1.  **Identify** implicit state distributed across hooks.
2.  **Extract** logic into a **Pure Reducer**.
3.  **Model** explicit **States/Modes** (Idle, Dragging, Fetching).
4.  **Decouple** using **Events** instead of setters.
5.  **Handle Effects** using **Commands** (return descriptions, don't execute).
6.  **Compose** domains via **Broadcasting**, **Mediator**, or a **Monolith**.