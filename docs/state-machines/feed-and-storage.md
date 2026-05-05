---
name: state-machines/feed-and-storage
description: State machines for feed loading, scrape form, the client article store, and mutation persistence.
last_updated: 2026-05-05 06:38, 36614cc
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
idle  →  ready                          (session cache hit, < 30 min old)
idle  →  fetching  →  ready             (no cache at all; scrape returns first)
idle  →  fetching  →  cached  →  merged (cache rendered first, then scrape merges in)
```

#### Three-Phase Flow

1. **Session cache check** — `sessionStorage` key `scrapeResults:{start}:{end}`, TTL 30 min. If hit, jump straight to `ready`.
2. **Phase 1 (cache-first)** — `POST /api/storage/daily-range` fetches cached payloads from Supabase. If any exist, render immediately (`cached`).
3. **Phase 2 (background scrape)** — `POST /api/scrape` fetches fresh data. If Phase 1 rendered, merge existing dates with `mergeDayFromServer()` preserving local state (lifecycle, summaries, digest, selection, expansion). New dates are initialized with `hydrateDay()`. If Phase 1 did not render, fresh payloads are hydrated before `ready`.

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
  │              │  merging_store
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

#### Merge Algorithm (`mergePreservingLocalState` + `mergeDayFromServer`)

Server-origin fields (`url`, `title`, `articleMeta`, `category`, `sourceId`, `section`, `sectionEmoji`, `sectionOrder`, `newsletterType`, `issueDate`) are overwritten from fresh scrape. Client-state fields (`read`, `removed`, `summary`, `digest`) are preserved from local cache and from the live article store.

**Modules:** `lib/feedMerge.js` contains the pure payload merge. `store/articleStore.js` ingests the merged payload into article/day slices.

#### Error Handling

- `AbortError` → silently ignored (component unmounted).
- Other errors → log, set empty results as fallback.

#### Propagation

```
useFeedLoader (results) → App → Feed → CalendarDay → NewsletterDay → ArticleList → ArticleCard
```

Feed results provide structural props for date/newsletter/section grouping. Live article, day, selection, summary, and container state comes from `articleStore` subscriptions.

`CalendarDay` consumes `useDayArticlesSummary(date)` for cached day-level derived state such as all-removed auto-folding.

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

### 8. Client Article Store and Mutation Queue

| | |
|---|---|
| **Pattern** | External store (`useSyncExternalStore`) + optimistic mutation queue |
| **Files** | `store/articleStore.js`, `lib/dailyPayloadMutations.js`, `lib/storageApi.js` |
| **Scope** | Module-level singleton backing app-wide article/day state |

#### Store State

| Structure | Purpose |
|---|---|
| `articleSlices` | Per-article live state keyed by article key. |
| `daySlices` | Per-date payload metadata, digest state, and ordered article keys. |
| `urlToArticleKey` | URL lookup for selection and summary commands. |
| Listener maps | Separate subscriptions for article, day, day-article-summary, container, and select-mode state. |
| Derived caches | Selected descriptors and day article summaries. |

#### Ingestion

| Operation | When |
|---|---|
| `hydrateDay(date, payload)` | Initial ingestion for cached/session/fresh payloads. |
| `mergeDayFromServer(date, payload)` | Background scrape updates an already rendered date. |
| `replaceDayFromServer(date, payload)` | Server-confirmed write or rollback refreshes a date wholesale. |

Ingestion also removes stale articles for the day so derived ordering and selection do not retain articles absent from the latest authoritative payload.

#### Optimistic Mutations

```
1. Build article or day patch.
2. Apply optimistic patch to articleStore.
3. Persist through daily payload API with expected storage_updated_at metadata.
4. On success: replace day from server-confirmed payload.
5. On conflict: refresh server payload and retry once.
6. On failure: restore day from server payload.
```

| API | Purpose |
|---|---|
| `queueDailyArticlePatch(date, url, patch)` | One article mutation. |
| `queueBatchArticlePatches(patches)` | Grouped article mutations; one payload write per date. |
| `queueDailyPayloadPatch(date, patch)` | Day-level mutation such as digest status. |

#### Server Endpoints

| Operation | Endpoint |
|---|---|
| Read day payload + metadata | `GET /api/storage/daily/{date}` |
| Patch one article | `PATCH /api/storage/daily/{date}/article` |
| Patch full daily payload | `PATCH /api/storage/daily/{date}` |

#### Cross-Component Sync

Store actions notify only the listener sets affected by a mutation: article listeners, day listeners, derived day-summary listeners, container listeners, and select-mode listeners. This replaces whole-payload pub/sub with slice-level invalidation.

---

### The Three Persistence Tiers

```
┌─────────────────────────────────────────────┐
│  Tier 1: articleStore                       │  ← Instant, same-tab
│  Populated by: feed hydration, scrape merge,│
│                optimistic mutations          │
├─────────────────────────────────────────────┤
│  Tier 2: sessionStorage                     │  ← Fast, survives re-render
│  Key: scrapeResults:{start}:{end}           │     but not tab close
│  TTL: 30 minutes                            │
├─────────────────────────────────────────────┤
│  Tier 3: Supabase PostgreSQL (daily_cache)  │  ← Durable, cross-device
│  Written via PATCH /api/storage/daily/...   │
│  Read via GET /api/storage/daily/{date}     │
└─────────────────────────────────────────────┘
```

Plus a separate `localStorage` tier for `expandedContainerIds` only.

Reads flow through feed loading and day hydration. Writes are optimistic: local store first → background persist → server replacement or rollback.

---
