---
last_updated: 2026-01-24 08:11, 6967463
---
# Scrape-First Hydration via Cache Seeding

## Overview

Eliminate redundant per-day network fan-out by seeding the `useSupabaseStorage` cache with the authoritative payload from `/api/scrape`. This preserves the existing pub/sub reactivity mechanism while removing unnecessary fetches.

## Current State Analysis

The app performs redundant network calls on refresh:

1. `/api/scrape` returns authoritative payloads for each day (already merged with cached state)
2. Each `CalendarDay` passes this payload to `useSupabaseStorage(key, payload)` as `defaultValue`
3. Despite having the payload, the hook **fetches from `/api/storage/daily/<date>` anyway** (line 145)
4. This causes N network calls for N days displayed—all redundant

The original plan (./plan.md) proposed removing `useSupabaseStorage` from CalendarDay, but the criticism (./plan-criticism.md) correctly identified this would break reactivity: when a user marks an article as read/removed, CalendarDay wouldn't re-render.

### Key Discoveries

- The hook's reactivity comes from the `subscribe()` mechanism at `useSupabaseStorage.js:167-187`
- When `setValueAsync()` runs, it updates `readCache` (line 201) **before** calling `emitChange()` (line 202)
- Subscribers' `handleChange()` calls `readValue()` which checks `readCache` first (line 44-46)
- So changes propagate via the in-memory cache, not via network refetch

**Critical insight:** If the cache is pre-populated, `readValue()` returns instantly with no network call. The subscription mechanism still works because it reads from the same cache.

## Desired End State

- On app load, `CalendarDay` renders immediately from the scrape payload with **no per-day fetch**
- No "Syncing..." flash in the day headers (loading starts as `false` when payload is provided)
- Article state changes (read/removed/tldr) still propagate to CalendarDay via the pub/sub mechanism
- `useArticleState` finds the payload already in cache—no fetch needed
- Server persistence continues unchanged via `writeValue()`

### Verification

- Network tab shows only `/api/scrape` on refresh, no `/api/storage/daily/*` calls
- Marking an article as read updates the `ReadStatsBadge` count immediately
- Removing all articles in a day triggers the auto-fold behavior
- State persists across page refresh

## What We're NOT Doing

- Not removing `useSupabaseStorage` from CalendarDay (subscription needed for reactivity)
- Not changing the hook's API or return signature
- Not modifying CalendarDay, ArticleCard, or useArticleState
- Not changing server-side logic or storage schema

## Implementation Approach

Seed the module-level `readCache` at hook initialization when a valid `defaultValue` is provided. This single change eliminates the redundant fetch while preserving all existing behavior.

## Phase 1: Cache Seeding in useSupabaseStorage

### Overview

Add cache-seeding logic at the start of the `useSupabaseStorage` hook. When `defaultValue` is non-null and the cache is empty for that key, seed the cache immediately. Initialize `loading` to `false` when no fetch is needed.

### Changes Required

#### 1. Cache seeding and loading state initialization
**File**: `client/src/hooks/useSupabaseStorage.js`
**Location**: Lines 135-140 (start of hook body)
**Changes**:

Before the existing state declarations, add cache-seeding logic:

```
+ // Seed cache with defaultValue to enable scrape-first hydration.
+ // CalendarDay provides the authoritative payload from /api/scrape;
+ // subsequent hooks (useArticleState) find it already cached.
+ const cacheWasEmpty = !readCache.has(key)
+ if (defaultValue != null && cacheWasEmpty) {
+   readCache.set(key, defaultValue)
+ }

  const [value, setValue] = useState(defaultValue)
- const [loading, setLoading] = useState(true)
+ // No fetch needed if we just seeded the cache or it was already populated
+ const [loading, setLoading] = useState(cacheWasEmpty && defaultValue == null)
```

The existing `readValue()` call in the first useEffect (line 145) will now:
- Hit the cache immediately (line 44-46)
- Return the seeded value with no network call
- The `setLoading(false)` at line 149 is now a no-op (already false)

No other changes needed—the fetch effect, subscription effect, and `setValueAsync` all work unchanged.

### Success Criteria

#### Automated Verification
- [ ] `source ./setup.sh` (environment validation)
- [ ] `source ./setup.sh && start_server_and_watchdog` (server start)
- [ ] `curl http://localhost:5001/api/scrape` (API responds)

#### Manual Verification
- [ ] Refresh the app with DevTools Network tab open
- [ ] Verify only `/api/scrape` is called for data (no `/api/storage/daily/*` requests)
- [ ] Day headers show no "Syncing..." flash on load
- [ ] Toggle an article's removed state; verify `ReadStatsBadge` count updates immediately
- [ ] Remove all articles in a day; verify the section auto-folds
- [ ] Refresh again; verify removed states persisted correctly
- [ ] Open TLDR on an article; verify it loads and persists

**Implementation Note**: This is a single-file, surgical change. After completing and verifying, the optimization is complete.

---

## Testing Strategy

### Unit Tests
None required—this is an internal optimization with no API changes.

### Integration Tests
Existing tests should pass unchanged since the hook's return values and behavior are preserved.

### Manual Testing Steps
1. Clear sessionStorage and hard refresh
2. Open Network tab, filter by "storage"
3. Verify zero `/api/storage/daily/*` requests
4. Interact with articles (toggle read, remove, fetch TLDR)
5. Verify all state changes reflect immediately in UI
6. Refresh and verify persistence

## References

- Original research: `thoughts/26-01-22-speed-up-app-refresh/research.md`
- Previous plan: `thoughts/26-01-22-speed-up-app-refresh/plan.md`
- Criticism: `thoughts/26-01-22-speed-up-app-refresh/plan-criticism.md`
- Key file: `client/src/hooks/useSupabaseStorage.js:135-164`
