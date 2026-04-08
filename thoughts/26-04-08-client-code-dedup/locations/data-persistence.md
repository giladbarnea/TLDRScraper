---
last_updated: 2026-04-08 20:31
---
# Data & Persistence Domain Analysis

**Scope:** `useSupabaseStorage.js`, `storageApi.js`, `storageKeys.js`
**Date:** 2026-04-08

---

## Executive Summary

The Data & Persistence domain has significant architectural issues that increase maintenance burden:

1. **Abstraction layer bypass:** `useSupabaseStorage.js` implements its own network I/O instead of using `storageApi.js`, rendering the API layer mostly dead code.
2. **Duplicated key routing logic:** The same key-pattern dispatch (`cache:` vs `newsletters:scrapes:`) exists in two places.
3. **Duplicated optimistic update pattern:** Two functions implement identical optimistic update flows.
4. **Mixed concerns in a single module:** Infrastructure (cache, pub/sub), business logic, and React integration all live in one file.

---

## Finding 1: Dead Code in `storageApi.js`

### Location

`client/src/lib/storageApi.js:1-37`

### Problem

Three of four functions are never imported or used:

```javascript
// Lines 1-9: NEVER USED
async function isDateCached(date) { ... }

// Lines 11-19: NEVER USED
async function getDailyPayload(date) { ... }

// Lines 21-34: NEVER USED
async function setDailyPayload(date, payload) { ... }

// Lines 36-50: ONLY EXPORTED FUNCTION
export async function getDailyPayloadsRange(startDate, endDate, signal) { ... }
```

### Evidence

```bash
$ grep -r "isDateCached\|getDailyPayload\|setDailyPayload" client/src --include="*.js" --include="*.jsx"
# Returns nothing - these functions are defined but never called
```

### Root Cause

`useSupabaseStorage.js` implements its own network calls inside `readValue()` and `writeValue()` (lines 44-71, 73-103), bypassing `storageApi.js` entirely:

```javascript
// useSupabaseStorage.js:53-60 - Direct fetch, no storageApi import
if (key.startsWith('cache:')) {
  const response = await window.fetch(`/api/storage/setting/${key}`)
  ...
} else if (key.startsWith('newsletters:scrapes:')) {
  const date = key.split(':')[2]
  const response = await window.fetch(`/api/storage/daily/${date}`)
  ...
}
```

### Impact

- **Maintenance burden:** Two parallel implementations of the same API calls
- **Confusion:** Future developers may add to `storageApi.js` not realizing it's bypassed
- **Bundle size:** Dead code ships to production

---

## Finding 2: Duplicated Key Routing Logic

### Location

`client/src/hooks/useSupabaseStorage.js:53-71` (readValue)
`client/src/hooks/useSupabaseStorage.js:77-100` (writeValue)

### Problem

Both functions contain identical key-pattern dispatch logic:

**In `readValue`:**
```javascript
if (key.startsWith('cache:')) {
  // ... fetch /api/storage/setting/${key}
} else if (key.startsWith('newsletters:scrapes:')) {
  const date = key.split(':')[2]
  // ... fetch /api/storage/daily/${date}
} else {
  console.warn(`Unknown storage key pattern: ${key}`)
}
```

**In `writeValue`:**
```javascript
if (key.startsWith('cache:')) {
  // ... POST /api/storage/setting/${key}
} else if (key.startsWith('newsletters:scrapes:')) {
  const date = key.split(':')[2]
  // ... POST /api/storage/daily/${date}
} else {
  throw new Error(`Unknown storage key pattern: ${key}`)
}
```

### Impact

- Adding a new key pattern requires changes in two places
- Inconsistent behavior (warning vs throwing on unknown patterns)
- Key extraction logic (`key.split(':')[2]`) duplicated

---

## Finding 3: Duplicated Optimistic Update Pattern

### Location

`client/src/hooks/useSupabaseStorage.js:116-133` (`setStorageValueAsync`)
`client/src/hooks/useSupabaseStorage.js:177-200` (`setValueAsync` inside hook)

### Problem

Both functions implement identical optimistic update flow:

**`setStorageValueAsync` (imperative):**
```javascript
const previous = await readValue(key, defaultValue)
const resolved = typeof nextValue === 'function' ? nextValue(previous) : nextValue
if (resolved === previous) return

readCache.set(key, resolved)
emitChange(key)

try {
  await writeValue(key, resolved)
} catch (error) {
  readCache.set(key, previous)
  emitChange(key)
  throw error
}
```

**`setValueAsync` (hook method):**
```javascript
const previous = valueRef.current
const resolved = typeof nextValue === 'function' ? nextValue(previous) : nextValue
if (resolved === previous) return

valueRef.current = resolved
setValue(resolved)
readCache.set(key, resolved)
emitChange(key)

try {
  await writeValue(key, resolved)
} catch (err) {
  valueRef.current = previous
  setValue(previous)
  readCache.set(key, previous)
  emitChange(key)
  throw err
}
```

### Differences

| Aspect | `setStorageValueAsync` | `setValueAsync` |
|--------|------------------------|-----------------|
| Previous value source | `readValue()` async | `valueRef.current` sync |
| React state update | No | Yes (`setValue()`) |
| Function update support | Yes | Yes |
| Return value | None | None |

### Impact

- Same logic maintained in two places
- Hook version does strictly more work (updates React state)
- Both call `writeValue()` for the actual network operation

---

## Finding 4: Mixed Concerns in Single Module

### Location

`client/src/hooks/useSupabaseStorage.js` (entire file, 236 lines)

### Problem

The module conflates three distinct concerns:

#### Concern 1: Infrastructure Layer (Lines 1-103)
- Module-level singletons: `changeListenersByKey`, `readCache`, `inflightReads`
- Pub/sub implementation: `emitChange()`, `subscribe()`
- Network I/O: `readValue()`, `writeValue()`

#### Concern 2: Imperative API (Lines 105-133)
- `getCachedStorageValue()` - cache getter
- `subscribeToStorageKey()` - pub/sub wrapper
- `setStorageValueAsync()` - imperative optimistic update

#### Concern 3: React Integration (Lines 135-236)
- `useSupabaseStorage()` hook with state management
- Cache seeding logic (lines 163-177)
- Effect subscriptions (lines 187-213)
- Hook-local optimistic update (lines 215-246)

### Evidence of Coupling

The hook directly manipulates infrastructure singletons:
```javascript
// Line 169: Direct cache mutation
readCache.set(key, defaultValue)

// Line 221: Direct cache mutation
readCache.set(key, resolved)

// Line 230: Direct pub/sub call
emitChange(key)
```

### Impact

- Hard to test individual concerns in isolation
- Cannot reuse infrastructure without React dependency
- Adding new storage patterns requires touching multiple sections
- Difficult to reason about data flow (imperative vs reactive paths)

---

## Finding 5: Inconsistent API Design

### Location

Two functions named `setStorageValueAsync` with different signatures:

1. `client/src/hooks/useSupabaseStorage.js:116` - exported function
2. `client/src/hooks/useSupabaseStorage.js:215` - hook method (named `setValueAsync` internally)

### Problem

Both do the same thing but with different interfaces:

**Exported function signature:**
```javascript
export async function setStorageValueAsync(key, nextValue, defaultValue = null)
```

**Hook method signature:**
```javascript
const setValueAsync = async (nextValue) => { ... }  // key from closure
```

The hook version requires instantiating the hook first (which requires a key), while the exported function can be called from anywhere but requires explicit default value.

### Impact

- Callers must understand two different calling conventions
- The exported function is used in `App.jsx` for batch operations
- The hook method is used in `useArticleState.js`
- Neither calls the other, so changes must be synchronized

---

## Finding 6: Unused Import in `storageKeys.js`

### Location

`client/src/lib/storageKeys.js:1-8`

### Problem

This file has only one exported function:
```javascript
export function getNewsletterScrapeKey(date) {
  return `newsletters:scrapes:${date}`
}
```

However, the key pattern `newsletters:scrapes:` is:
1. Constructed here for external consumers
2. Hardcoded in `useSupabaseStorage.js:56,78` as a string literal

### Evidence

```bash
$ grep -r "newsletters:scrapes:" client/src --include="*.js" --include="*.jsx"
client/src/hooks/useSupabaseStorage.js:    } else if (key.startsWith('newsletters:scrapes:')) {
client/src/hooks/useSupabaseStorage.js:    if (key.startsWith('newsletters:scrapes:')) {
client/src/lib/storageKeys.js:  return `newsletters:scrapes:${date}`
```

### Impact

- Key pattern defined in two places
- Changing the pattern requires updating both
- `storageKeys.js` is the "source of truth" but `useSupabaseStorage.js` doesn't use it

---

## Summary Table

| Finding | Severity | Effort | Impact |
|---------|----------|--------|--------|
| Dead code in `storageApi.js` | Medium | Low | Removes ~35 lines of unused code |
| Duplicated key routing | High | Medium | Single source of truth for routing |
| Duplicated optimistic update | High | Medium | Reduces bugs from divergent logic |
| Mixed concerns | High | High | Improves testability and maintainability |
| Inconsistent API | Medium | Low | Reduces cognitive load |
| Key pattern duplication | Low | Low | Single source of truth |

---

## Recommended Actions (Not Implementation)

1. **Consolidate storage API:** Either remove `storageApi.js` entirely (move `getDailyPayloadsRange` elsewhere) or have `useSupabaseStorage.js` use it instead of direct fetch.

2. **Extract key routing:** Create a single `resolveStorageEndpoint(key)` function that returns `{ method, url, body }` for both read and write operations.

3. **Unify optimistic update:** Make `setValueAsync` inside the hook call the exported `setStorageValueAsync`, adding React state updates as a side effect via pub/sub.

4. **Split concerns:** Consider:
   - `storageCache.js` - module-level cache, pub/sub, inflight dedup
   - `storageClient.js` - network operations
   - `useSupabaseStorage.js` - React hook only

5. **Use key constants:** Import and use `getNewsletterScrapeKey()` or export the prefix constant from `storageKeys.js`.

---

## Files Referenced

| File | Lines | Role |
|------|-------|------|
| `client/src/hooks/useSupabaseStorage.js` | 1-236 | Main storage hook and infrastructure |
| `client/src/lib/storageApi.js` | 1-50 | API client (mostly unused) |
| `client/src/lib/storageKeys.js` | 1-8 | Key pattern builder |
