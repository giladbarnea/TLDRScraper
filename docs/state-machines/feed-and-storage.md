---
name: state-machines/feed-and-storage
description: State machines for feed loading, scrape form, and Supabase storage.
last_updated: 2026-05-02 11:36
---
# State Machines: Feed and Storage

[→ Server: Scraping Pipeline](../server/scraping-pipeline.md) | [→ Server: Storage](../server/storage.md) | [→ Client: Feed Loading](../client/feed-loading.md) | [→ Client: Storage](../client/storage.md)

### 5. Feed Loading

| | |
|---|---|
| **Pattern** | `useState` + `useCallback` in custom hook |
| **File** | `hooks/useFeedLoader.js` |
| **Scope** | Singleton — consumed by `App.jsx` and `ScrapeForm.jsx` |

#### States

```
idle  →  ready                          (session cache hit, < 10 min old)
idle  →  fetching  →  ready             (no cache at all; scrape returns first)
idle  →  fetching  →  cached  →  merged (cache rendered first, then scrape merges in)
```

#### Three-Phase Flow

1. **Session cache check** — `sessionStorage` key `scrapeResults:{start}:{end}`, TTL 10 min. If hit, jump straight to `ready`.
2. **Phase 1 (cache-first)** — `POST /api/storage/daily-range` fetches cached payloads from Supabase. If any exist, render immediately (`cached`).
3. **Phase 2 (background scrape)** — `POST /api/scrape` fetches fresh data. If Phase 1 rendered, merge new articles via `mergeIntoCache()` preserving local state (read/removed/summary). If Phase 1 didn't render, set results directly (`ready`).

**Unified entry point:** Both `App.jsx` (on mount) and `ScrapeForm.jsx` (on submit) call `useFeedLoader.loadFeed()`. This ensures consistent cache-first + merge behavior regardless of entry point.

#### Unified Scrape Journey (Cross-Stack)

The full scrape journey spans `ScrapeForm`, app-level Feed Loading, and the server's per-date scrape policy. Feed Loading owns the cached-render and merge phases, but the end-to-end machine is slightly larger:

```
idle
  │
  ├─ User submits date range
  │    ↓
  │  validating
  │    │
  │    ├─ Invalid dates
  │    │    ↓
  │    │  error
  │    │
  │    └─ Valid dates
  │         ↓
  │       checking_cache
  │         │
  │         ├─ Session cache hit
  │         │    ↓
  │         │  complete
  │         │
  │         ├─ Past dates fully cached in Supabase
  │         │    ↓
  │         │  complete
  │         │
  │         └─ Cache miss or today in range
  │              ↓
  │            fetching_api
  │              │
  │              ├─ Server policy for past dates: cache-first per date
  │              ├─ Server policy for today: union cached articles + fresh scrape
  │              │
  │              ├─ Success
  │              │    ↓
  │              │  merging_cache
  │              │    ↓
  │              │  complete
  │              │
  │              └─ Failure
  │                   ↓
  │                 error
  │
  └─ Next request returns to idle
```

**Why this matters:** `today` bypasses the all-cached shortcut so the server can still scrape and union late-published articles into the cached payload.

**Key state data:** `startDate`, `endDate`, `loading`, `progress`, `error`, `results`.

#### Merge Algorithm (`mergePreservingLocalState`)

Server-origin fields (`url`, `title`, `articleMeta`, `category`, `sourceId`, `section`, `sectionEmoji`, `sectionOrder`, `newsletterType`, `issueDate`) are overwritten from fresh scrape. Client-state fields (`read`, `removed`, `summary`, `digest`) are preserved from local cache.

**Module:** `lib/feedMerge.js` — contains `mergePreservingLocalState()` and `SERVER_ORIGIN_FIELDS` constant.

#### Error Handling

- `AbortError` → silently ignored (component unmounted).
- Other errors → log, set empty results as fallback.

#### Propagation

```
useFeedLoader (results) → App → Feed → CalendarDay → NewsletterDay → ArticleList → ArticleCard
```

`CalendarDay` seeds the `readCache` in `useSupabaseStorage` with its payload prop, preventing redundant per-day API calls.

**Selection utilities:** `lib/selectionUtils.js` provides `getSelectedArticles()`, `extractSelectedArticleDescriptors()`, and `groupSelectedByDate()` for working with selected articles across payloads.

---

### 10. Scrape Form

| | |
|---|---|
| **Pattern** | `useState` + `useActionState` (React 19) |
| **File** | `components/ScrapeForm.jsx` |
| **Scope** | Singleton (in settings panel) |

#### States

```
idle  →  pending  →  success  (onSuccess called, settings close)
              ↓
            error   (validation or network)
```

#### Validation

- Start ≤ end date.
- Range ≤ 31 days.

#### Simulated Progress

Client-side only: starts at 10%, increments 5% every 500ms capped at 90%, jumps to 100% on success, resets to 0% on error. Does not reflect actual server progress.

#### Integration

`loadFeed({ startDate, endDate, useSessionCache: false })` → calls `useFeedLoader.loadFeed()` with the user's date range. This flows through the same cache-first + merge logic as the app mount, ensuring consistent behavior. `onSuccess()` callback closes the settings panel.

**Date range utility:** Uses `getDefaultFeedDateRange()` from `useFeedLoader` for consistent default range calculation (today - 2 days to today).

### 8. Supabase Storage

| | |
|---|---|
| **Pattern** | Custom hook with module-level cache + pub/sub |
| **File** | `hooks/useSupabaseStorage.js` |
| **Scope** | Per-key instance; module-level singletons shared across all instances |

#### Module-Level Singletons

| Singleton | Type | Purpose |
|---|---|---|
| `readCache` | `Map<key, value>` | In-memory cache. Source of truth between renders. |
| `inflightReads` | `Map<key, Promise>` | Request deduplication. Prevents N parallel fetches for the same key. |
| `changeListenersByKey` | `Map<key, Set<fn>>` | Pub/sub. Any `emitChange(key)` notifies all subscribers for that key. |

#### Hook State

```js
const [value, setValue]     = useState(defaultValue)
const [loading, setLoading] = useState(…)
const [error, setError]     = useState(null)
```

#### Optimistic Update (`setValueAsync`)

```
1. Snapshot previous value
2. Optimistic: update React state + readCache + emitChange()
3. Background: writeValue() → POST to server
4. On error: revert React state + readCache + emitChange() + set error
```

#### Key Routing

| Key pattern | Read endpoint | Write endpoint |
|---|---|---|
| `newsletters:scrapes:{date}` | `GET /api/storage/daily/{date}` | `POST /api/storage/daily/{date}` |
| `cache:{setting}` | `GET /api/storage/setting/{key}` | `POST /api/storage/setting/{key}` |

#### Cache Seeding

`CalendarDay` passes the authoritative payload from `/api/scrape` as `defaultValue`. The hook seeds `readCache` if the key is empty, preventing N redundant API calls when ArticleCards mount.

#### Cross-Component Sync

`emitChange(key)` does two things:
1. Calls all registered listeners for that key (same-tab, same-render-tree).
2. Dispatches `window.CustomEvent('supabase-storage-change')` (cross-tab, listened by `App.jsx` to force re-render).

#### Imperative API

`setStorageValueAsync(key, nextValue)` — same optimistic pattern but callable outside React components. Used by `applyBatchLifecyclePatch()` in `App.jsx` and `updateArticlesAcrossDates()` in `useDigest`.

---

### The Three Persistence Tiers

```
┌─────────────────────────────────────────────┐
│  Tier 1: Module-level readCache (Map)       │  ← Instant, same-tab
│  Populated by: cache seeding, API reads,    │
│                optimistic writes             │
├─────────────────────────────────────────────┤
│  Tier 2: sessionStorage                     │  ← Fast, survives re-render
│  Key: scrapeResults:{start}:{end}           │     but not tab close
│  TTL: 10 minutes                            │
├─────────────────────────────────────────────┤
│  Tier 3: Supabase PostgreSQL (daily_cache)  │  ← Durable, cross-device
│  Written via POST /api/storage/daily/{date} │
│  Read via GET /api/storage/daily/{date}     │
└─────────────────────────────────────────────┘
```

Plus a separate `localStorage` tier for `expandedContainerIds` only.

Reads cascade: readCache → (if miss) inflightReads dedup → API → cache + return.
Writes are optimistic: local first → background persist → revert on failure.

---
