---
last_updated: 2026-02-20 07:52
---
# Client-Side Storage and State Persistence System Analysis

## Overview

The client-side storage layer is a pub/sub reactive cache system that routes all persistence to Supabase PostgreSQL via Flask API routes. It uses key-based routing patterns to determine which Supabase table to write to and implements cross-component synchronization through an event-driven architecture.

## Entry Points

1. `/home/user/TLDRScraper/client/src/lib/storageApi.js` - HTTP wrapper functions for storage endpoints
2. `/home/user/TLDRScraper/client/src/lib/storageKeys.js` - Storage key pattern generator
3. `/home/user/TLDRScraper/client/src/hooks/useSupabaseStorage.js` - Reactive storage hook with pub/sub
4. `/home/user/TLDRScraper/client/src/hooks/useArticleState.js` - Article-specific state management
5. `/home/user/TLDRScraper/client/src/App.jsx:15-29,82-95` - Payload hydration and merge logic
6. `/home/user/TLDRScraper/serve.py:114-219` - Backend storage API routes

---

## Core Implementation

### 1. Storage API Layer (`storageApi.js`)

Simple HTTP wrapper functions that call Flask endpoints. All functions follow GET/POST patterns:

**Responsibilities:**
- `isDateCached(date)` → `GET /api/storage/is-cached/{date}` - Check if date exists in cache
- `getDailyPayload(date)` → `GET /api/storage/daily/{date}` - Fetch single day payload
- `setDailyPayload(date, payload)` → `POST /api/storage/daily/{date}` - Persist single day payload
- `getDailyPayloadsRange(startDate, endDate, signal)` → `POST /api/storage/daily-range` - Bulk fetch date range

**Data Transformations:**
- All responses unwrap from `{ success: boolean, ... }` envelope format
- `getDailyPayload` returns `data.payload` or `null` (no error throw)
- `getDailyPayloadsRange` returns `data.payloads` array
- Errors throw exceptions with message from `data.error`

**Integration Points:**
- Consumed by `App.jsx` for initial feed hydration
- Consumed by `useSupabaseStorage.js` internally (via key-based routing)

### 2. Storage Key Patterns (`storageKeys.js:6-8`)

Single function that generates keys for the daily cache table:

**Responsibilities:**
- `getNewsletterScrapeKey(date)` → `"newsletters:scrapes:{date}"`

**Key Pattern Rules:**
- Keys starting with `"cache:"` → route to `settings` table
- Keys starting with `"newsletters:scrapes:"` → route to `daily_cache` table
- Unknown patterns → console warning and no-op

**Purpose:**
- Used by `useSupabaseStorage` to parse the key and determine routing
- Used by `useArticleState` to construct storage keys for article state

### 3. Reactive Storage Hook (`useSupabaseStorage.js`)

Core of the storage system. Implements a memory-cached, pub/sub reactive layer over the backend API.

#### Module-Level State (Lines 3-5)

```javascript
const changeListenersByKey = new Map()  // key → Set<listener>
const readCache = new Map()             // key → value
const inflightReads = new Map()         // key → Promise<value>
```

- `changeListenersByKey`: Cross-component subscription registry
- `readCache`: In-memory cache to avoid redundant fetches
- `inflightReads`: Deduplication for concurrent reads of same key

#### Cache Seeding for Scrape-First Hydration (Lines 135-159)

**Purpose:**
Eliminates redundant per-day storage fetches by seeding cache with payload from `/api/scrape`.

**Flow:**
1. CalendarDay receives authoritative payload from `/api/scrape`
2. CalendarDay passes payload as `defaultValue` to `useSupabaseStorage(key, payload)`
3. Hook checks if `readCache.has(key)` is false (line 156)
4. If cache empty and `defaultValue != null`, seed cache: `readCache.set(key, defaultValue)`
5. Subsequent `readValue()` hits cache instantly - no `/api/storage/daily/{date}` fetch

**Critical Constraint:**
DO NOT REMOVE. Without this, each CalendarDay would trigger `/api/storage/daily/{date}` on mount, causing N redundant fetches and flashing "Syncing..." indicators.

#### readValue (Lines 41-86)

**Responsibilities:**
- Check `readCache` for immediate return
- Check `inflightReads` to await existing fetch
- Parse key pattern to route to correct endpoint
- Fetch from backend and cache result

**Key Routing Logic (Lines 56-71):**
```javascript
if (key.startsWith('cache:')) {
  // Route to settings table: GET /api/storage/setting/{key}
} else if (key.startsWith('newsletters:scrapes:')) {
  // Route to daily_cache table: GET /api/storage/daily/{date}
  const date = key.split(':')[2]
} else {
  console.warn(`Unknown storage key pattern: ${key}`)
}
```

**Data Flow:**
- Input: `key`, `defaultValue`
- Output: Promise of cached or fetched value
- Side Effects: Updates `readCache`, clears `inflightReads`

#### writeValue (Lines 88-133)

**Responsibilities:**
- Route write to correct backend endpoint based on key pattern
- Update `readCache` optimistically
- Call `emitChange(key)` to notify subscribers

**Key Routing Logic (Lines 92-125):**
```javascript
if (key.startsWith('cache:')) {
  // POST /api/storage/setting/{key} with { value }
} else if (key.startsWith('newsletters:scrapes:')) {
  // POST /api/storage/daily/{date} with { payload: value }
  const date = key.split(':')[2]
} else {
  throw new Error(`Unknown storage key pattern: ${key}`)
}
```

**Data Flow:**
- Input: `key`, `value`
- Output: void (throws on error)
- Side Effects: Updates backend, updates `readCache`, calls `emitChange(key)`

#### emitChange (Lines 7-22)

**Responsibilities:**
- Notify all subscribers for a given key
- Dispatch global `CustomEvent` on window

**Cross-Component Sync Mechanism:**
1. Component A calls `setValueAsync(newValue)`
2. `writeValue()` updates cache and calls `emitChange(key)`
3. `emitChange()` iterates `changeListenersByKey.get(key)` and calls each listener
4. Component B's subscription (from line 206) fires `handleChange()`
5. `handleChange()` calls `readValue(key)` → reads from updated cache → `setValue(newValue)`
6. Both components now have synchronized state

**Window Event (Lines 19-21):**
```javascript
window.dispatchEvent(new CustomEvent('supabase-storage-change', { detail: { key } }))
```
Not consumed anywhere in current codebase - vestigial or for future extension.

#### subscribe / unsubscribe (Lines 24-39)

**Responsibilities:**
- Register listener for a key
- Return cleanup function
- Auto-cleanup `changeListenersByKey` when last listener removed

**Data Flow:**
- Input: `key`, `listener` function
- Output: cleanup function
- Side Effects: Adds listener to Map, returns unsubscribe function

#### useSupabaseStorage Hook (Lines 135-249)

**Hook Interface:**
```javascript
const [value, setValueAsync, remove, { loading, error }] = useSupabaseStorage(key, defaultValue)
```

**Responsibilities:**
- Cache seeding (lines 156-159)
- Initial load via `readValue()` (lines 167-189)
- Subscribe to changes (lines 192-212)
- Optimistic updates via `setValueAsync()` (lines 214-242)
- Automatic rollback on write failure (lines 233-240)

**setValueAsync Flow (Lines 214-242):**
1. Resolve functional updater: `typeof nextValue === 'function' ? nextValue(previous) : nextValue`
2. Bail early if `resolved === previous`
3. **Optimistic:** Update local state immediately (lines 223-227)
4. **Background:** Persist via `writeValue(key, resolved)` (line 231)
5. **Rollback on Failure:** Revert to `previous` and re-emit (lines 234-240)

**Loading State (Line 162):**
```javascript
const [loading, setLoading] = useState(cacheWasEmpty && defaultValue == null)
```
Only `true` initially if cache empty AND no defaultValue provided.

#### mergeIntoCache (Lines 251-257)

**Responsibilities:**
- Update cache with merge function without triggering a backend write
- Emit change to notify subscribers

**Use Case:**
Called from `App.jsx:92-95` to merge fresh scrape results into cache while preserving local article state.

**Data Flow:**
- Input: `key`, `mergeFn(currentValue) → mergedValue`
- Output: void
- Side Effects: Updates `readCache`, calls `emitChange(key)`

### 4. Article State Hook (`useArticleState.js`)

Wrapper around `useSupabaseStorage` for article-specific mutations.

**Responsibilities:**
- Construct storage key via `getNewsletterScrapeKey(date)`
- Extract single article from payload by URL
- Compute lifecycle state via `getArticleLifecycleState(article)`
- Provide article mutation functions (markAsRead, toggleRemove, etc.)

**Key Implementation (Lines 20-33):**
```javascript
const updateArticle = (updater) => {
  setPayload(current => {
    return {
      ...current,
      articles: current.articles.map(a =>
        a.url === url ? { ...a, ...updater(a) } : a
      )
    }
  })
}
```

**Data Flow:**
1. `dispatchLifecycleEvent(event)` (lines 35-44)
2. Calls `reduceArticleLifecycle(current, event)` to compute patch
3. Calls `updateArticle(a => patch)` to immutably update article in payload
4. `setPayload` (from `useSupabaseStorage`) triggers optimistic update + backend write
5. `emitChange(key)` notifies all components subscribed to this date's key

**Integration Points:**
- Consumed by `ArticleCard` to manage read/removed states
- Mutations propagate to all cards for the same date via pub/sub

### 5. App.jsx Payload Hydration (`App.jsx:15-29,62-115`)

#### mergePreservingLocalState (Lines 15-29)

**Responsibilities:**
Merge fresh scrape results with local cached payload while preserving user state (read/removed).

**Algorithm:**
1. Build `Map<url, article>` from `localPayload.articles`
2. Map over `freshPayload.articles`
3. For each fresh article:
   - If exists in local: cherry-pick server-origin fields from fresh, merge onto local
   - If new: return fresh article as-is
4. Server-origin fields (line 13): `['url', 'title', 'articleMeta', 'issueDate', 'category', 'sourceId', 'section', 'sectionEmoji', 'sectionOrder', 'newsletterType']`

**Purpose:**
Allows scraper to update article metadata (title, section, etc.) while preserving client-side state (`read`, `removed`, `tldr`).

#### Two-Phase Load (Lines 62-115)

**Phase 1: Render cached data immediately (lines 68-76)**
1. Fetch from `getDailyPayloadsRange(startDate, endDate)` (reads from `daily_cache` table)
2. If any payloads returned, render immediately: `setResults({ payloads: cachedPayloads })`
3. Set `phase1Rendered = true`

**Phase 2: Merge background scrape results (lines 78-110)**
1. Await `/api/scrape` (background fetch from newsletter sources)
2. If phase1 rendered:
   - For overlapping dates: call `mergeIntoCache(key, local => mergePreservingLocalState(fresh, local))`
   - For new dates: append to results
3. If phase1 NOT rendered (no cache):
   - Render scrape results directly

**Data Flow:**
```
[Cache Empty]
  → Scrape → Render

[Cache Hit]
  → Render Cache → Scrape → Merge → Re-render
```

**Critical Optimization:**
`mergeIntoCache` updates the cache and emits change events, causing all CalendarDay components to re-read from cache and re-render with merged data. No manual React state updates needed.

### 6. Backend Storage Routes (`serve.py:114-219`)

All routes follow envelope pattern: `{ success: boolean, data?, error? }`

**GET /api/storage/setting/{key} (Lines 114-130)**
- Calls `storage_service.get_setting(key)`
- Returns 404 if not found
- Returns `{ success: true, value }`

**POST /api/storage/setting/{key} (Lines 132-148)**
- Expects `{ value }` in body
- Calls `storage_service.set_setting(key, value)`
- Upserts to `settings` table

**GET /api/storage/daily/{date} (Lines 150-166)**
- Calls `storage_service.get_daily_payload(date)`
- Returns 404 if not found
- Returns `{ success: true, payload }`

**POST /api/storage/daily/{date} (Lines 168-184)**
- Expects `{ payload }` in body
- Calls `storage_service.set_daily_payload(date, payload)`
- **Critical:** Uses `set_daily_payload()` (NOT `set_daily_payload_from_scrape()`)
- Does NOT update `cached_at` timestamp (intentional - only scraper updates `cached_at`)
- Upserts to `daily_cache` table

**POST /api/storage/daily-range (Lines 186-204)**
- Expects `{ start_date, end_date }` in body
- Calls `storage_service.get_daily_payloads_range(start_date, end_date)`
- Returns `{ success: true, payloads: [payload1, payload2, ...] }`

**GET /api/storage/is-cached/{date} (Lines 206-219)**
- Calls `storage_service.is_date_cached(date)`
- Returns `{ success: true, is_cached: boolean }`

---

## Data Flow

### Article State Update Flow

1. User clicks "Mark as Read" in `ArticleCard`
2. `ArticleCard` calls `markAsRead()` from `useArticleState(date, url)`
3. `useArticleState` → `dispatchLifecycleEvent({ type: MARK_READ, markedAt })`
4. `reduceArticleLifecycle()` computes patch: `{ read: { isRead: true, markedAt } }`
5. `updateArticle(a => patch)` → `setPayload(current => { ...current, articles: [...] })`
6. `setPayload` (from `useSupabaseStorage`) → `setValueAsync(newPayload)`
7. `setValueAsync` → Optimistic update: `setValue(newPayload)`, `readCache.set(key, newPayload)`, `emitChange(key)`
8. `emitChange(key)` → Calls all listeners for `key`
9. All `ArticleCard` components for this date re-render with updated state
10. Background: `writeValue(key, newPayload)` → `POST /api/storage/daily/{date}` → Upsert to `daily_cache` table

### Initial Feed Load Flow

1. `App.jsx` mounts → `useEffect` fires (line 35)
2. Compute date range: last 3 days
3. Fetch cached payloads: `getDailyPayloadsRange(startDate, endDate)` → `GET /api/storage/daily-range` → Returns `[payload1, payload2, ...]`
4. Render cached: `setResults({ payloads: cachedPayloads })`
5. Background: `scrapeNewsletters(startDate, endDate)` → `POST /api/scrape` → Returns fresh payloads
6. For each fresh payload:
   - If date in cache: `mergeIntoCache(key, local => mergePreservingLocalState(fresh, local))`
   - If new date: append to results
7. `mergeIntoCache` → `readCache.set(key, merged)`, `emitChange(key)`
8. All CalendarDay components for merged dates re-render with updated articles

### Cache Seeding Flow (Eliminates Redundant Fetches)

1. `App.jsx` calls `scrapeNewsletters()` → Returns `{ payloads: [payload1, payload2, ...] }`
2. `Feed` receives payloads and maps to `<CalendarDay payload={payload} />`
3. `CalendarDay` renders and internally calls `useSupabaseStorage(key, payload)`
4. `useSupabaseStorage` checks `readCache.has(key)` → `false` (cache empty)
5. Check `defaultValue != null` → `true` (payload provided)
6. Seed cache: `readCache.set(key, payload)` (line 158)
7. Set loading state: `setLoading(false)` (line 162)
8. `useEffect` (line 167) calls `readValue(key, payload)`
9. `readValue` hits cache immediately (line 44): `return readCache.get(key)`
10. No backend fetch triggered
11. ArticleCard mounts and calls `useArticleState(date, url)`
12. `useArticleState` calls `useSupabaseStorage(key, null)`
13. Cache already seeded from CalendarDay → Instant return, no fetch

---

## Key Patterns

### Pub/Sub Reactivity

**Pattern:** Event-driven cross-component synchronization

**Implementation:**
- Module-level `Map` of listeners (`changeListenersByKey`)
- `emitChange(key)` iterates and calls all listeners
- Each `useSupabaseStorage` hook subscribes to its key (line 206)
- Subscription fires `handleChange()` → `readValue(key)` → `setValue(newValue)`

**Example:**
- Component A: `useSupabaseStorage("newsletters:scrapes:2024-01-01")`
- Component B: `useSupabaseStorage("newsletters:scrapes:2024-01-01")`
- Component A calls `setValueAsync(newValue)`
- `emitChange` fires → Component B's subscription fires → Both components have synchronized state

### Optimistic Updates with Rollback

**Pattern:** Update UI immediately, persist in background, rollback on failure

**Implementation (Lines 214-242):**
1. Update `valueRef.current`, `setValue()`, `readCache.set()`, `emitChange()` immediately
2. Persist via `writeValue()` in background
3. On error: Revert to `previous`, re-emit

**Benefit:**
- Instant UI feedback (no loading spinners on every mutation)
- Automatic recovery from network failures

### Cache-First with Scrape-Merge

**Pattern:** Render cached data instantly, merge fresh scrape results in background

**Implementation (`App.jsx:62-115`):**
1. Phase 1: Fetch and render cache immediately
2. Phase 2: Scrape fresh data in background
3. Merge fresh into cache via `mergeIntoCache` (preserves local state)
4. Pub/sub re-renders all components with merged data

**Benefit:**
- Instant first render (perceived performance)
- Always shows latest data after scrape completes
- No lost user state (read/removed preserved)

### Key-Based Routing

**Pattern:** Use key prefix to determine backend endpoint and table

**Implementation (`useSupabaseStorage.js:56-71,92-125`):**
```javascript
if (key.startsWith('cache:')) {
  // → settings table
} else if (key.startsWith('newsletters:scrapes:')) {
  // → daily_cache table
}
```

**Benefit:**
- Single hook interface for all storage types
- Easy to extend (add new key pattern → add routing logic)
- Clear separation of concerns (settings vs daily data)

---

## Configuration

No configuration files. Routing patterns are hardcoded in `useSupabaseStorage.js`.

**Key Patterns:**
- `"cache:*"` → `settings` table
- `"newsletters:scrapes:{date}"` → `daily_cache` table

**Backend Tables (Per ARCHITECTURE.md:965-986):**

**settings:**
```sql
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**daily_cache:**
```sql
CREATE TABLE daily_cache (
  date DATE PRIMARY KEY,
  payload JSONB NOT NULL,
  cached_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Error Handling

**Read Errors (`readValue`, lines 76-79):**
- Catch all errors
- Log to console: `console.error(...)`
- Return `defaultValue`
- Clear inflight promise

**Write Errors (`writeValue`, lines 129-132):**
- Catch all errors
- Log to console: `console.error(...)`
- Throw error (propagates to caller)

**Hook-Level Error Handling (`useSupabaseStorage`, lines 176-183):**
- Catch read errors
- Set `error` state
- Set `value` to `defaultValue`
- Set `loading` to `false`

**Optimistic Rollback (`setValueAsync`, lines 233-240):**
- Catch write errors
- Revert `valueRef.current`, `value`, `readCache` to `previous`
- Call `emitChange(key)` to sync rollback across components
- Set `error` state
- Throw error

---

## Recommendations for Article Digest Feature

### Option 1: Store in `daily_cache` Alongside Articles

**Storage Location:**
Add `digest` field to daily payload:

```javascript
{
  date: "2024-01-01",
  articles: [...],
  digest: {
    summary: "...",
    generatedAt: "...",
    version: 1
  }
}
```

**Key Pattern:**
Use existing `"newsletters:scrapes:{date}"` key

**Pros:**
- Zero new infrastructure (same table, same routes, same hooks)
- Digest automatically cached with articles
- Existing merge logic preserves digest across scrapes
- Single source of truth per day

**Cons:**
- Couples digest lifecycle to article payload
- Every article state update writes entire payload including digest
- Cannot invalidate digest independently of articles

**Implementation Complexity:** Low

---

### Option 2: New Storage Key Pattern for Digests

**Storage Location:**
Use `settings` table with new key pattern:

```javascript
Key: "digest:{date}"
Value: {
  summary: "...",
  generatedAt: "...",
  version: 1
}
```

**Backend Routes:**
Already exist: `GET/POST /api/storage/setting/{key}`

**Client Usage:**
```javascript
const [digest, setDigest] = useSupabaseStorage(`digest:${date}`, null)
```

**Pros:**
- Independent lifecycle from articles
- Can invalidate/regenerate digest without touching articles
- Cleaner separation of concerns
- No payload bloat on every article mutation

**Cons:**
- Semantically incorrect (settings table is for app config, not content)
- Two separate fetches per day (articles + digest)
- Digest not included in `/api/storage/daily-range` response

**Implementation Complexity:** Low

---

### Option 3: New Table for Digests

**Storage Location:**
New `daily_digests` table:

```sql
CREATE TABLE daily_digests (
  date DATE PRIMARY KEY,
  digest JSONB NOT NULL,
  generated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Backend Routes:**
New routes needed:
- `GET /api/storage/digest/{date}`
- `POST /api/storage/digest/{date}`
- `POST /api/storage/digest-range` (optional)

**Backend Service:**
New functions in `storage_service.py`:
- `get_digest(date)`
- `set_digest(date, digest)`

**Client Storage Key:**
New pattern: `"digest:{date}"`

**Client Hook Routing:**
Add case to `useSupabaseStorage.js`:

```javascript
if (key.startsWith('digest:')) {
  const date = key.split(':')[1]
  const response = await fetch(`/api/storage/digest/${date}`)
  // ...
}
```

**Pros:**
- Clean separation of concerns (articles vs digests)
- Independent schema evolution
- Can add digest-specific indexes/constraints
- Semantically correct
- Digest invalidation independent of articles

**Cons:**
- Requires backend migration
- New routes + service functions
- New client-side routing logic
- Separate fetches per day (can batch via range endpoint)

**Implementation Complexity:** Medium

---

### Recommendation: Option 1 (Store in `daily_cache`)

**Rationale:**
1. Minimal implementation effort (zero new infrastructure)
2. Digest is conceptually part of "what happened today" (same scope as articles)
3. Existing merge logic handles it correctly
4. Single fetch per day (better perceived performance)
5. Payload size increase is negligible (digest is small text)

**Caveat:**
If digests need frequent regeneration or independent invalidation, consider Option 3 later.

**Next Steps:**
1. Update `DailyPayload` type in backend to include optional `digest` field
2. Update scraper/summarizer to generate digest and include in payload
3. Client automatically receives digest via existing `useSupabaseStorage` flow
4. Add UI component to display digest
5. Existing merge logic preserves digest across scrapes

---

## Summary

The client-side storage system is a **reactive, cache-first, pub/sub architecture** that routes all persistence to Supabase PostgreSQL. It implements:

1. **Key-based routing:** Storage keys determine which table/endpoint to use
2. **Memory cache:** In-memory Map prevents redundant fetches
3. **Pub/sub reactivity:** Cross-component synchronization via event listeners
4. **Optimistic updates:** Instant UI feedback with automatic rollback on error
5. **Cache seeding:** Scrape-first hydration eliminates redundant storage fetches
6. **Merge-preserving updates:** Fresh scrape results merged with local state

For article digests, **store in `daily_cache` alongside articles** (Option 1) for minimal implementation complexity and automatic cache/merge behavior.
