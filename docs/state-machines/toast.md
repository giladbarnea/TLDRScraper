---
name: state-machines/toast
description: State machine for toast notifications and global pub/sub.
last_updated: 2026-05-29 12:02
---
# State Machines: Toast

### 18. Toast

| | |
|---|---|
| **Pattern** | `useState([])` + pub/sub via `toastBus.js` |
| **File** | `components/ToastContainer.jsx`, `lib/toastBus.js` |
| **Scope** | Singleton (rendered at app root) |

#### State

- **Container**: `toasts: Array<{ id, title, onOpen }>`, max 2 (`.slice(-2)`).
- **Per-toast**: `exiting: boolean` (drives exit animation class).

#### Single Trigger Point

`store/articleStore.js` emits toasts from `summaryActions.fetch()` on successful summary fetch:
```
emitToast({ title: article.title, onOpen: expand })
```

#### Lifecycle

```
0ms        → Toast appears (animate-toast-in: slide down + fade + scale)
11,650ms   → exiting=true (animate-toast-out: slide up + fade + scale)
12,000ms   → Removed from state
```

Clicking a toast calls `onOpen()` (expands the summary overlay) then dismisses it.

#### Separate Error Toast

`ArticleCard` has a separate inline `ErrorToast` component (red, bottom-positioned, 5s auto-dismiss) for gesture errors. It does **not** use `toastBus` — it's local to the card and driven by `gestureReducer.errorMessage`.

---

### Pub/Sub Boundary

#### `toastBus.js`

Global `Set<callback>`. One publisher (`summaryActions.fetch` on fetch success in `store/articleStore.js`). One subscriber (`ToastContainer`).

Direction: Summary Data success → Toast notification → (click) → Summary View expand.

Selection-dock article actions no longer use a separate pub/sub bridge. `App.jsx` resolves selected descriptors from `articleStore` and calls store-backed summary actions by article key. Toasts remain a dedicated bus because they are global, transient UI notifications rather than article state.

---
