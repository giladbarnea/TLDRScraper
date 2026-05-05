---
name: state-machines/articles-and-summaries
description: State machines for article lifecycle, summary data, digest, and the Zen lock.
last_updated: 2026-05-05 12:01
---
# State Machines: Articles and Summaries

[→ Server: Articles & Data](../server/articles-and-data.md) | [→ Server: Summaries](../server/summaries.md) | [→ Client: Articles & Lifecycle](../client/articles-and-lifecycle.md) | [→ Client: Summaries & Digests](../client/summaries-and-digests.md)

### The Article Slice: Shared Substrate

Most machines don't talk to each other directly. They converge on a **shared article slice** in `articleStore`. The daily payload remains the durable transport/persistence shape, but the live UI reads and writes article slices.

```js
{
  // Server-origin (overwritten on scrape merge)
  url, title, articleMeta, issueDate, category,
  sourceId, section, sectionEmoji, sectionOrder, newsletterType,

  // Client-state: Article Lifecycle domain
  removed: boolean,
  read: { isRead: boolean, markedAt: string | null },

  // Client-state: Summary Data domain
  summary: {
    status: 'unknown' | 'loading' | 'available' | 'error',
    markdown: string,
    effort: string,
    checkedAt: string | null,
    errorMessage: string | null,
  },

  // Client-view state stripped before persistence
  selected: boolean,
  expandedView: boolean,
  originalOrder: number,
}

// Sibling to articles on the payload:
payload.digest: {
  status, markdown, articleUrls, generatedAt, effort, errorMessage
}
```

Article Lifecycle and Summary Data are **two independent domains on the same slice**. They never read each other's fields inside their reducers. The coupling happens at the _consumer_ level — e.g., `ArticleCard` reads both `isRemoved` and `summary.status` and decides what to render.

`sliceToArticle()` strips UI-only fields such as selection, expansion, and original order before composing a daily payload for persistence.

---

### 1. Article Lifecycle

| | |
|---|---|
| **Pattern** | Pure reducer function (no `useReducer` — called imperatively) |
| **File** | `reducers/articleLifecycleReducer.js` |
| **Dispatched via** | `hooks/useArticleState.js` → reducer patch → `queueDailyArticlePatch()` / `queueBatchArticlePatches()` |

#### States

```
UNREAD  →  READ  →  REMOVED
  ↑          ↑         |
  └──────────┴─────────┘  (RESTORE / TOGGLE_REMOVED)
```

`removed` takes precedence: a removed-and-read article is `REMOVED`.

#### Events

| Event | Transition | Payload |
|---|---|---|
| `MARK_READ` | any → READ (stays REMOVED if removed) | `markedAt` |
| `MARK_UNREAD` | any → UNREAD (stays REMOVED if removed) | — |
| `TOGGLE_READ` | READ ↔ UNREAD | `markedAt` |
| `MARK_REMOVED` | any → REMOVED | — |
| `TOGGLE_REMOVED` | REMOVED ↔ previous | — |
| `RESTORE` | REMOVED → READ or UNREAD | — |

#### Dispatch Sites

| Who | File | When |
|---|---|---|
| `useArticleState` action methods | `hooks/useArticleState.js` | Individual article tap/swipe/overlay-close |
| `applyBatchLifecyclePatch()` | `App.jsx` | Selection dock "Mark Read" / "Mark Removed" via grouped batch patches |
| `markDigestArticlesConsumed()` | `hooks/useDigest.js` | Digest overlay close |
| `ArticleCard.handleSummaryClose()` | `components/ArticleCard.jsx` | Closing a summary overlay can mark the article READ |

#### Consumers

| Who | What it reads | Why |
|---|---|---|
| `ArticleCard` | `isRead`, `isRemoved` | Visual styling, conditional rendering, disable selection |
| `ArticleList` | `article.removed` | Sort removed articles to bottom |
| `ReadStatsBadge` | Live article slices resolved from `(date, url)` via `articleStore` | Completion count (`read` or `removed` / total) |
| `CalendarDay`, `NewsletterDay` | `articles.every(a => a.removed)` | Auto-fold when all removed |
| `useSwipeToRemove` | `isRemoved` | Disable drag when removed |
| `interactionReducer` | `isDisabled(id)` predicate resolving article slice | Prevent selecting removed articles |

#### Persistence

State lives on the article slice (`removed: bool`, `read: { isRead, markedAt }`) and is persisted back into the daily payload. Single-article writes use `queueDailyArticlePatch()`. Batch writes use `queueBatchArticlePatches()` and are grouped into one daily payload write per date.

---

### 2. Summary Data

| | |
|---|---|
| **Pattern** | Pure reducer function (called imperatively, like Article Lifecycle) |
| **File** | `reducers/summaryDataReducer.js` |
| **Dispatched via** | `hooks/useSummary.js`, `hooks/useDigest.js`, `App.jsx` |
| **Markdown rendering** | Overlay components memoize sanitized HTML with `lib/markdownUtils.js` |

#### States

```
UNKNOWN  →  LOADING  →  AVAILABLE
                ↓
              ERROR
                ↓
   ROLLBACK → (previous state)
```

#### Events

| Event | Transition | Payload |
|---|---|---|
| `SUMMARY_REQUESTED` | → LOADING | `effort` |
| `SUMMARY_LOAD_SUCCEEDED` | → AVAILABLE | `markdown`, `effort`, `checkedAt` |
| `SUMMARY_LOAD_FAILED` | → ERROR | `errorMessage` |
| `SUMMARY_RESET` | → UNKNOWN | — |
| `SUMMARY_ROLLBACK` | → whatever `previousData` was | `previousData` |

#### Dispatch Sites

| Who | File | When |
|---|---|---|
| `useSummary.fetchSummary()` | `hooks/useSummary.js` | User taps article → fetch single summary |
| `useSummary` abort handler | `hooks/useSummary.js` | AbortError → ROLLBACK |
| `useDigest.markDigestArticlesLoading()` | `hooks/useDigest.js` | Digest triggered → marks each article LOADING |
| `useDigest` success/error/abort | `hooks/useDigest.js` | Digest response → writes digest-level status |

#### Consumers

| Who | What | Why |
|---|---|---|
| `useSummary` | `status`, `markdown`, `expandedView` | Orchestrates summary commands and overlay state |
| `ZenModeOverlay` | `markdown` → sanitized HTML | Renders summary overlay content with KaTeX math support |
| `DigestOverlay` | `markdown` → sanitized HTML | Renders digest overlay content with KaTeX math support |
| `ArticleCard` | `summary.status`, `summary.isAvailable`, `summary.errorMessage` | Status indicators, error display |
| `App.jsx` | `getSummaryDataStatus()` | Determines which selection actions are available |

#### Persistence

Summary data (`{ status, markdown, effort, checkedAt, errorMessage }`) lives on `article.summary` in the article slice. Digest data lives on the day slice and persists as `payload.digest`. Both use the daily payload mutation layer.

---

### 6. Digest

| | |
|---|---|
| **Pattern** | `useState` + async effects + `summaryDataReducer` for status |
| **File** | `hooks/useDigest.js` |
| **Scope** | Singleton (created in `App.jsx`) |
| **Dependencies** | `lib/zenLock.js` (zen lock), `lib/requestUtils.js` (request tokens), `lib/dailyPayloadMutations.js` |

#### States

```
idle  →  triggering  →  [pending payload load]  →  loading  →  available
                                                       ↓
                                                     error
```

`triggering` is a local boolean; `loading`/`available`/`error` are `summaryDataReducer` states stored on `payload.digest`.

#### Trigger Flow

1. User selects 2+ articles → clicks "Digest" in `SelectionActionDock`.
2. `trigger(articleDescriptors)` checks for cache hit (same URL set → just expand). Otherwise sets `pendingRequest` + `targetDate` + `triggering=true`.
3. A `useEffect` watches for `pendingRequest` + payload loaded → kicks off `runDigest()`.
4. `runDigest()`: marks all participating articles' summaries as LOADING → `POST /api/digest` → on success: restore article summaries, write digest status AVAILABLE, clear selection, `expand()`.

#### Rollback

On abort or error, `restoreDigestArticlesSummary()` restores each article's `summary` field from a snapshot taken before the request. This undoes the LOADING indicators.

#### Cross-Date Operations

`updateArticlesAcrossDates()` groups article URLs by their `issueDate`, then performs `queueBatchArticlePatches()` so a single digest operation writes once per affected date. This is necessary because articles in one digest may span multiple days.

#### Zen Lock

Digest acquires the lock with owner `'digest'` (constant). If a single-article summary is already open, digest expansion is blocked, and vice versa.

---

### 7. Summary View

| | |
|---|---|
| **Pattern** | Store-backed `expandedView` boolean + summary data from `summaryDataReducer` |
| **File** | `hooks/useSummary.js` |
| **Scope** | Per-article instance (created in each `ArticleCard`) |
| **Dependencies** | `lib/zenLock.js` (zen lock), `lib/requestUtils.js` (request tokens), `store/articleStore.js` |

#### Dual State

- **Data state** (persistent): `article.summary.status` — `unknown → loading → available / error`. Managed by `summaryDataReducer`.
- **View state** (client slice): `expandedView: boolean`. Controls whether the `ZenModeOverlay` portal renders.

#### `toggle(effort)` Decision Tree

```
isAvailable?
  ├─ yes, expanded  → collapse()
  ├─ yes, !expanded → acquireZenLock(url) → summaryActions.expand(articleKey)
  └─ no             → fetchSummary(effort)
```

#### `collapse()`

1. Release zen lock.
2. Set `expandedView=false` through `summaryActions.collapse(articleKey)`.

Mark-read-on-close is owned by `ArticleCard`, which calls `markAsRead()` from `useArticleState` when the overlay close path requests it.

#### Abort / Request Token Pattern

- Each `fetchSummary()` call creates a new `AbortController` (aborting any previous) and a unique `requestToken`.
- Stale responses are discarded by comparing `requestTokenRef.current !== requestToken`.
- `AbortError` triggers `SUMMARY_ROLLBACK` to restore previous summary data.

#### Toast Emission

On successful fetch, `emitToast({ title, url, onOpen: expand })` fires. The toast's click handler calls `expand()`, opening the overlay.

---

### Zen Lock: The Mutual-Exclusion Protocol

A module-level variable in `lib/zenLock.js`:

```js
let zenLockOwner = null   // string | null
```

| Operation | Semantics |
|---|---|
| `acquireZenLock(owner)` | If `null`, set to `owner`, return `true`. Else return `false`. |
| `releaseZenLock(owner)` | If `zenLockOwner === owner`, set to `null`. |

**Who acquires:**
- `useSummary.toggle()` / `expand()` → owner = `article.url`
- `useDigest.expand()` → owner = `'digest'`

**Who releases:**
- `useSummary.collapse()` + cleanup effect on unmount
- `useDigest.collapse()` + cleanup effect on unmount

**Effect:** At most one overlay (one Zen Mode OR one Digest) can be expanded at any time. This prevents overlapping portals and ensures the body scroll lock (`document.body.style.overflow = 'hidden'`) is managed by a single owner.

---
