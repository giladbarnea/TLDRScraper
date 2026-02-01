---
last_updated: 2026-02-01 21:30, 7a9f8f1
---
# ArticleCard interaction states: suggestion + rationale

## Context terminology update
- What used to be "TLDR" in the "summary" sense — not the TLDR newsletter, not  this project's name — has been renamed to **"summary"**.
- Zen overlay completion is now **pull-to-remove**, which maps directly to the card-level **removed** state (no longer called "done")

---

## Suggested state modeling

### Domain A — Article lifecycle (persistent, stored)
**States**
- `unread`
- `read`
- `removed`

**Notes**
- This domain owns the storage contract and is the only source of truth for read/removed.
- `removed` is a terminal-like visual state but still reversible by a user action (restore).

### Domain B — Summary data (async)
**States**
- `unknown`
- `loading`
- `available`
- `error`

**Notes**
- This domain is strictly about data availability and API state.
- `available` is orthogonal to whether the summary is expanded in the UI.
- The naming is now consistent with the "summary" rename.

### Domain C — Summary view (UI)
**States**
- `collapsed`
- `expanded`

**Notes**
- `expanded` is the Zen overlay open state (single-owner lock).
- The overlay may only be opened if summary is `available` (no fetch on open), or if you explicitly allow “open → fetch → render”.

### Domain D — Gesture / interaction (UI)
**States**
- `idle`
- `dragging`
- `select-mode`

**Notes**
- `dragging` gates taps, mirrors swipe-to-remove.
- `select-mode` reinterprets tap as “select” instead of “open summary.”
- This domain is global because selection spans multiple cards.

---

## Why split into multiple state machines (vs. a single monolith)

### 1) Existing coupling already matches orthogonal domains
- Read/removed are persisted and should not depend on transient UI interaction state.
- Summary data is async and independent of selection/dragging.
- Overlay open/close is a view concern and not durable state.

A monolithic machine would create a combinatorial explosion of states without new product value.

### 2) Better separation of “data state” vs “view state”
- `summary.available` can coexist with `summaryView.collapsed`.
- `removed` can coexist with `summaryView.expanded` only when the user intentionally performs the “pull-to-remove” action; that action becomes the transition that closes the overlay and sets removed.

### 3) Clearer product behavior at edges
Splitting lets you define crisp cross-domain transitions without inventing new global states:
- **Event:** `PULL_TO_REMOVE_COMPLETED`
  - **Lifecycle:** `removed = true`
  - **Summary view:** `expanded = false`
  - **Summary data:** unchanged

---

## Recommended coordination (minimal mediator)
Use a small orchestrator layer (or reducer composition) that only translates **outcomes** into the other domains’ events.

**Example transitions**
- `SUMMARY_REQUESTED` → Summary data: `loading`
- `SUMMARY_LOADED` → Summary data: `available`; Summary view: `expanded`
- `SUMMARY_OPENED` (user tap) → Summary view: `expanded`
- `SUMMARY_CLOSED` → Summary view: `collapsed`
- `PULL_TO_REMOVE_COMPLETED` → Summary view: `collapsed`; Lifecycle: `removed`

This keeps each reducer "closed" while still coordinating product-level rules.

---

## Final answer to “single vs. split”
**Split** into multiple state machines, and coordinate via a minimal mediator or reducer composition. The separation matches the product intent: lifecycle is durable, summary data is async, summary view is transient, and gestures/selection are global interaction modes. Keeping them separate prevents accidental state coupling and avoids a fragile monolithic reducer.
