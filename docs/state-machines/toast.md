---
name: state-machines/toast
description: State machine for toast notifications and global pub/sub buses.
last_updated: 2026-05-03 15:10, bb6b54a
---
# State Machines: Toast

### 18. Toast

| | |
|---|---|
| **Pattern** | `useState([])` + pub/sub via `toastBus.js` |
| **File** | `components/ToastContainer.jsx`, `lib/toastBus.js` |
| **Scope** | Singleton (rendered at app root) |

#### State

- **Container**: `toasts: Array<{ id, title, url, onOpen }>`, max 2 (`.slice(-2)`).
- **Per-toast**: `exiting: boolean` (drives exit animation class).

#### Single Trigger Point

Only `useSummary.js` emits toasts — on successful summary fetch:
```
emitToast({ title: article.title, url, onOpen: expand })
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

### The Two Pub/Sub Buses

#### 1. `toastBus.js`

Global `Set<callback>`. One publisher (`useSummary` on fetch success). One subscriber (`ToastContainer`).

Direction: Summary Data success → Toast notification → (click) → Summary View expand.

#### 2. `articleActionBus.js`

Per-URL `Map<url, Set<callback>>`. Publishers: `App.jsx` selection actions (`publishArticleAction(urls, 'fetch-summary' | 'open-summary')`). Subscriber: `ArticleCard` (via `subscribeToArticleAction`).

Direction: Selection dock action → bridge to per-card summary hooks without prop drilling.

Both buses exist to cross component boundaries that would otherwise require prop drilling through the Feed → CalendarDay → NewsletterDay → ArticleList → ArticleCard hierarchy.

---
