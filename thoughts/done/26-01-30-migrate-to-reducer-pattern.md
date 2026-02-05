---
last_updated: 2026-02-05 16:11, b78c041
---
# Migrate Client-Side State to Reducer Pattern

Migrated ArticleCard state from scattered `useState` hooks to closed reducer pattern with explicit FSMs across 4 orthogonal domains:

**Domain A (Article Lifecycle)**: `unread` → `read` → `removed`. Closed reducer with event-driven transitions, storage patches, and transition logging. Only logs actual state changes (not no-ops).

**Domain B (Summary Data)**: `unknown` → `loading` → `available`/`error`. Closed reducer with request tokens to prevent stale updates, rollback-on-abort for canceled fetches, and persisted status.

**Domain C (Summary View)**: `collapsed` ↔ `expanded`. Initially implemented as reducer, then simplified to `useState(boolean)` after realizing view toggle doesn't justify reducer complexity. Kept zen lock coordination.

**Domain D (Gesture Interaction)**: `idle` → `dragging` → (error). Closed reducer for swipe-to-remove state. Select-mode remained in existing `interactionReducer`.

Benefits: eliminated impossible states, removed guard clause spaghetti, centralized transition logic, made side effects explicit. Preserved all functionality while reducing cognitive load.

Files: `client/src/reducers/{articleLifecycleReducer,summaryDataReducer,gestureReducer}.js`, `client/src/hooks/{useArticleState,useSummary,useSwipeToRemove}.js`. Deleted: `summaryViewReducer.js` (over-engineered).
