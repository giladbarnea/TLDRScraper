---
last_updated: 2026-05-02 10:48
---

# State Machines: Articles and Summaries

[→ Server: Articles & Data](../server/articles-and-data.md) | [→ Server: Summaries](../server/summaries.md) | [→ Client: Articles & Lifecycle](../client/articles-and-lifecycle.md) | [→ Client: Summaries & Digests](../client/summaries-and-digests.md)

### The Article Object: Shared Substrate

Most machines don't talk to each other directly. They converge on a **shared data object** — the article — stored inside the daily payload. This is the implicit coupling medium.

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

  // Injected at render time (not persisted)
  originalOrder: number,
}

// Sibling to articles on the payload:
payload.digest: {
  status, markdown, articleUrls, generatedAt, effort, errorMessage
}
```

Article Lifecycle and Summary Data are **two independent domains on the same object**. They never read each other's fields inside their reducers. The coupling happens at the _consumer_ level — e.g., `ArticleCard` reads both `isRemoved` and `summary.status` and decides what to render.

---

### 1. Article Lifecycle

| | |
|---|---|
| **Pattern** | Pure reducer function (no `useReducer` — called imperatively) |
| **File** | `reducers/articleLifecycleReducer.js` |
| **Dispatched via** | `hooks/useArticleState.js` → `updateArticle()` → `useSupabaseStorage.setValueAsync()` |

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
| `applyBatchLifecyclePatch()` | `App.jsx` | Selection dock "Mark Read" / "Mark Removed" |
| `markDigestArticlesConsumed()` | `hooks/useDigest.js` | Digest overlay close |
| `useSummary.collapse()` | `hooks/useSummary.js` | Closing a summary overlay marks article READ |

#### Consumers

| Who | What it reads | Why |
|---|---|---|
| `ArticleCard` | `isRead`, `isRemoved` | Visual styling, conditional rendering, disable selection |
| `ArticleList` | `article.removed` | Sort removed articles to bottom |
| `ReadStatsBadge` | `article.read?.isRead`, `article.removed` | Completion count |
| `CalendarDay`, `NewsletterDay` | `articles.every(a => a.removed)` | Auto-fold when all removed |
| `useSwipeToRemove` | `isRemoved` | Disable drag when removed |
| `InteractionContext` | `isRemoved` via `registerDisabled` | Prevent selecting removed articles |

#### Persistence

State lives on the article object (`removed: bool`, `read: { isRead, markedAt }`) inside the daily payload. Written to Supabase via `useSupabaseStorage` → `POST /api/storage/daily/{date}`.

---

### 2. Summary Data

| | |
|---|---|
| **Pattern** | Pure reducer function (called imperatively, like Article Lifecycle) |
| **File** | `reducers/summaryDataReducer.js` |
| **Dispatched via** | `hooks/useSummary.js`, `hooks/useDigest.js`, `App.jsx` |
| **Markdown→HTML** | `lib/markdownUtils.js` — `markdownToHtml()` converts markdown to sanitized HTML with KaTeX support |

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
| `useSummary` | `status`, `markdown` → `html` (via `markdownToHtml`) | Renders summary overlay content |
| `useDigest` | `status`, `markdown` → `html` (via `markdownToHtml`) | Renders digest overlay content with KaTeX math support |
| `ArticleCard` | `summary.status`, `summary.isAvailable`, `summary.errorMessage` | Status indicators, error display |
| `App.jsx` | `getSummaryDataStatus()` | Determines which selection actions are available |

#### Persistence

Summary data (`{ status, markdown, effort, checkedAt, errorMessage }`) lives on `article.summary` (or `payload.digest` for digests) inside the daily payload. Same Supabase storage path as Article Lifecycle.

---

### 6. Digest

| | |
|---|---|
| **Pattern** | `useState` + async effects + `summaryDataReducer` for status |
| **File** | `hooks/useDigest.js` |
| **Scope** | Singleton (created in `App.jsx`) |
| **Dependencies** | `lib/zenLock.js` (zen lock), `lib/markdownUtils.js` (markdown→HTML with KaTeX), `lib/requestUtils.js` (request tokens) |

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
4. `runDigest()`: marks all participating articles' summaries as LOADING → `POST /api/digest` → on success: restore article summaries, write digest status AVAILABLE, `clearSelection()`, `expand()`.

#### Rollback

On abort or error, `restoreDigestArticlesSummary()` restores each article's `summary` field from a snapshot taken before the request. This undoes the LOADING indicators.

#### Cross-Date Operations

`updateArticlesAcrossDates()` groups article URLs by their `issueDate`, then performs `setStorageValueAsync()` per date. This is necessary because articles in a single digest may span multiple days.

#### Zen Lock

Digest acquires the lock with owner `'digest'` (constant). If a single-article summary is already open, digest expansion is blocked, and vice versa.

---

### 7. Summary View

| | |
|---|---|
| **Pattern** | `useState(false)` for `expanded` boolean + summary data from `summaryDataReducer` |
| **File** | `hooks/useSummary.js` |
| **Scope** | Per-article instance (created in each `ArticleCard`) |
| **Dependencies** | `lib/zenLock.js` (zen lock), `lib/markdownUtils.js` (markdown→HTML), `lib/requestUtils.js` (request tokens) |

#### Dual State

- **Data state** (persistent): `article.summary.status` — `unknown → loading → available / error`. Managed by `summaryDataReducer`.
- **View state** (ephemeral): `expanded: boolean`. Controls whether the `ZenModeOverlay` portal renders.

#### `toggle(effort)` Decision Tree

```
isAvailable?
  ├─ yes, expanded  → collapse()
  ├─ yes, !expanded → acquireZenLock(url) → setExpanded(true)
  └─ no             → fetchSummary(effort)
```

#### `collapse(markAsReadOnClose = true)`

1. Release zen lock.
2. `setExpanded(false)`.
3. If `markAsReadOnClose && !isRead` → `markAsRead()` (fires Article Lifecycle `MARK_READ`).

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
