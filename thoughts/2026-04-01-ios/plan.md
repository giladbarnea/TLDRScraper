---
last_updated: 2026-04-08 08:18
---
# iOS Plan: JavaScriptCore Reducer Bridge

## Context

TLDRScraper is a Vite+React web app with a reading-queue / todo-for-articles mental model. We're adding a native iOS app. The iOS project already exists on the `ios` branch with a basic SwiftUI Hello World running in the simulator.

The main concern: keeping the web and iOS apps behaviorally in sync — not just types and API contracts, but actual user interaction flows and state machines.

## State Machines in the Codebase

There are 4 pure reducer files in `client/src/reducers/`:

- **`articleLifecycleReducer.js`** — `(article, event) → {state, patch}`. States: `UNREAD → READ → REMOVED`. Events: `MARK_READ`, `MARK_UNREAD`, `TOGGLE_READ`, `MARK_REMOVED`, `TOGGLE_REMOVED`, `RESTORE`. The patch is what gets persisted to Supabase.
- **`interactionReducer.js`** — `(state, event) → {state, decision}`. Handles selection mode, container expand/collapse, long-press/short-press, and a `suppressNextShortPress` debounce latch. Returns a `decision` (e.g. `shouldOpenItem`) to drive UI side effects.
- **`gestureReducer.js`** — `(state, event) → state`. States: `IDLE`, `DRAGGING`. Governs swipe/drag overlay feedback.
- **`summaryDataReducer.js`** — `(summaryData, event) → {state, patch}`. States: `UNKNOWN → LOADING → AVAILABLE | ERROR`. Tracks async fetch state for article summaries.

React wiring lives in `InteractionContext.jsx` (wraps interaction + gesture state via Context) and `useArticleState.js` (hooks into Supabase storage and applies lifecycle reducer). These are the only framework-dependent parts.

## Key Insight

All 4 reducers are **pure vanilla JS functions with zero framework dependencies**. No React, no browser APIs (except `Date.now()` in interactionReducer, which JavaScriptCore supports natively). This means they can be executed directly on iOS without any porting.

## Plan: JavaScriptCore Bridge

**Approach:** Run the JS reducer files directly in iOS via Apple's built-in `JavaScriptCore.framework`. The JS files become the single source of truth — executed on both platforms. Zero behavioral drift by construction.

**Steps:**
- [x] Move the 4 reducer files to `shared/reducers/` at the monorepo root  
  status: done
- [ ] Symlink (or copy at Xcode build time via a Build Phase script) into the app bundle
- [x] In Swift, implement a `ReducerBridge` class that:
  - [x] Loads the JS files into a `JSContext`
  - [x] Exposes a `dispatch(state: [String: Any], event: [String: Any]) -> [String: Any]` method
  - [x] Handles JSON serialization/deserialization at the boundary  
    status: done
- [ ] SwiftUI view models call `ReducerBridge.dispatch(...)` the same way React's `useReducer` would
- [ ] Thin Swift enums can optionally wrap event/state types as a typed facade (optional, for ergonomics)

**What this gives:**
- Zero drift by construction — same code path on both platforms
- No codegen pipeline to maintain
- JS unit tests cover both platforms simultaneously
- Adding a new event or state in JS automatically works on iOS

**Trade-off:** State is passed as JSON blobs rather than native Swift types. Acceptable at this scale; typed Swift facades can be added incrementally later without touching the bridge.

## What Is NOT Shared (By Design)

The UI trigger layer is intentionally platform-specific:
- Web: React event handlers, `onClick`, `onPointerDown`, drag events
- iOS: `TapGesture`, `LongPressGesture`, `DragGesture` in SwiftUI

The machine handles *what* happens; the platform decides *how* it's triggered.
