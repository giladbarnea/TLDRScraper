---
last_updated: 2026-04-08 20:32, 4b2172d
scope: Domain Hooks (useSummary.js, useDigest.js, useArticleState.js, articleActionBus.js, toastBus.js)
---
# Domain Hooks Analysis

## High-Value Opportunities

### 1. **Duplicated `createRequestToken()` Function** ⭐ HIGH

**Files:** `useSummary.js:67`, `useDigest.js:56`

```js
// useSummary.js:67
const createRequestToken = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`

// useDigest.js:56
const createRequestToken = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`
```

**Impact:** Identical function defined in two places. If token format needs to change (e.g., adding entropy, debugging info), both locations must be updated.

**Recommendation:** Extract to `lib/requestUtils.js` or similar.

---

### 2. **Duplicated Markdown→HTML Pipeline** ⭐ HIGH

**Files:** `useSummary.js:29-40`, `useDigest.js:33-40`

```js
// useSummary.js:29-40
const html = (() => {
  if (!markdown) return ''
  try {
    const rawHtml = marked.parse(markdown)
    return DOMPurify.sanitize(rawHtml, {
      ADD_TAGS: ['annotation', 'semantics']
    })
  } catch (error) {
    console.error('Failed to parse markdown:', error)
    return ''
  }
})()

// useDigest.js:33-40
const html = (() => {
  if (!markdown) return ''
  try {
    return DOMPurify.sanitize(marked.parse(markdown))
  } catch {
    return ''
  }
})()
```

**Problems:**
1. **Inconsistent behavior:** `useSummary.js` supports KaTeX (via `marked.use(markedKatexExtension)`) and adds `ADD_TAGS` for MathML elements. `useDigest.js` does neither.
2. **Duplicated imports:** Both files import `DOMPurify` and `marked`.
3. **Different error handling:** `useSummary.js` logs errors; `useDigest.js` silently swallows them.

**Impact:** Digest overlay won't render math correctly. Future bugs when one implementation diverges further.

**Recommendation:** Create `lib/markdownUtils.js` with a single `markdownToHtml(markdown, options?)` function. Configure KaTeX once at module level.

---

### 3. **Zen Lock Lives in useSummary.js** ⭐ MEDIUM

**Files:** `useSummary.js:11-22`

The zen lock functions are:
- Defined in `useSummary.js`
- Exported and imported by `useDigest.js`

```js
// useSummary.js
let zenLockOwner = null

export function acquireZenLock(owner) { ... }
export function releaseZenLock(owner) { ... }

// useDigest.js
import { acquireZenLock, releaseZenLock } from './useSummary'
```

**Problems:**
1. **Misplaced responsibility:** Zen lock is an overlay coordination primitive, not summary-specific. Its location in `useSummary.js` suggests ownership that doesn't exist.
2. **Implicit coupling:** `useDigest.js` depends on `useSummary.js` for infrastructure, not for summary behavior. This creates a hidden dependency graph.

**Impact:** If `useSummary.js` is refactored or the zen lock semantics change, the digest feature breaks silently. New developers may not realize the coupling exists.

**Recommendation:** Move zen lock to `lib/zenLock.js` or `lib/overlayCoordination.js`.

---

### 4. **Mixed Concerns in useDigest.js** ⭐ MEDIUM

**File:** `useDigest.js`

`useDigest` handles multiple distinct concerns:

1. **Digest state management** (`data`, `status`, `html`, `expanded`)
2. **Cross-date article updates** (`updateArticlesAcrossDates`, `markDigestArticlesLoading`, `restoreDigestArticlesSummary`, `markDigestArticlesConsumed`)
3. **Date/URL resolution** (`groupDescriptorsByDate`, `findMostRecentDate`)
4. **Zen lock coordination**
5. **AbortController / request token management**

**Problems:**
- **Complexity density:** The `useEffect` at line 121-171 contains nested async function, try/catch blocks, multiple state updates, and cross-cutting error handling.
- **Hard to test:** Individual behaviors cannot be unit tested in isolation.
- **Hard to modify:** Adding a new digest behavior requires navigating 200+ lines.

**Recommendation:** Consider extracting:
- `updateArticlesAcrossDates` → utility function in `lib/articleBatchUpdates.js`
- `groupDescriptorsByDate` → utility function (already a `useCallback`, but could be pure)

---

### 5. **Inconsistent Error Handling Patterns** ⭐ LOW

**Files:** `useSummary.js:97-115`, `useDigest.js:155-165`

Both hooks handle errors, but with different approaches:

```js
// useSummary.js - logs to console, sets errorMessage
console.error(`Failed to fetch ${type}:`, error)

// useDigest.js - wraps entire collapse in try/catch with console.error
catch (error) {
  console.error(`Failed to persist digest consumed lifecycle: ${error.message}`)
}
```

**Impact:** Low, but inconsistency makes debugging harder. Centralized error logging would help trace issues.

---

### 6. **setPayloadRef Pattern in useDigest.js** ⭐ LOW

**File:** `useDigest.js:50-51`

```js
const setPayloadRef = useRef(null)
setPayloadRef.current = setPayload
```

This stores the `setPayload` function in a ref to use it inside `writeDigest` (a `useCallback`). This is a workaround for stale closure capture.

**Problem:** Indicates the hook has too many moving parts. The `writeDigest` callback needs the setter, but `setPayload` changes on every render.

**Impact:** Low, but signals architectural tension. If React's behavior around closure captures changes, this pattern could break.

**Alternative:** Consider using `useReducer` for digest state, or restructuring the async flow.

---

## Not Concerns

### `articleActionBus.js` and `toastBus.js`

Both are clean, minimal pub/sub implementations. No issues.

### `useArticleState.js`

This hook is well-scoped: a thin facade over `useSupabaseStorage` and `articleLifecycleReducer`. It correctly delegates concerns to the reducer and storage layers.

---

## Summary Table

| Issue | Severity | File(s) | Lines |
|-------|----------|---------|-------|
| Duplicated `createRequestToken()` | HIGH | useSummary.js, useDigest.js | 67, 56 |
| Duplicated markdown→HTML pipeline (inconsistent!) | HIGH | useSummary.js, useDigest.js | 29-40, 33-40 |
| Zen lock lives in useSummary.js | MEDIUM | useSummary.js | 11-22 |
| Mixed concerns in useDigest.js | MEDIUM | useDigest.js | entire file |
| Inconsistent error handling | LOW | useSummary.js, useDigest.js | 97-115, 155-165 |
| setPayloadRef workaround | LOW | useDigest.js | 50-51 |

---

## Recommended Extraction Targets

1. **`lib/markdownUtils.js`** — `markdownToHtml(markdown, options?)`
2. **`lib/requestUtils.js`** — `createRequestToken()`
3. **`lib/zenLock.js`** — `acquireZenLock(owner)`, `releaseZenLock(owner)`, `getZenLockOwner()`
4. **`lib/articleBatchUpdates.js`** (optional) — `updateArticlesAcrossDates(urlsByDate, updater)`

---

## Files Analyzed

- `client/src/hooks/useSummary.js` (144 lines)
- `client/src/hooks/useDigest.js` (205 lines)
- `client/src/hooks/useArticleState.js` (67 lines)
- `client/src/lib/articleActionBus.js` (27 lines)
- `client/src/lib/toastBus.js` (13 lines)
