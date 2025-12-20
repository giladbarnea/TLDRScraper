---
last_updated: 2025-12-20 16:56
---
# Hooks Refactoring Implementation Plan

Based on the verified review response at `hooks-refactor-plan.review-response.md`.

---

## Implementation Priorities

Following the review response's revised priorities:
1. Remove dead code first (clear wins)
2. Simplify abort/finally logic (clarity improvement)
3. Extract pure functions (still valuable)
4. Skip ARTICLE_STATE constants (unused)

---

## 1. useSummary.js Refactoring

### 1.1 Remove Dead Code
**Lines to remove:**
- `buttonLabel` (lines 53-57): Computed but never used by consumers
- `toggleVisibility` function (lines 149-158): Never called by ArticleCard
- Export of `buttonLabel` (line 177)
- Export of `toggleVisibility` (line 182)

**Verification:** Grep confirms ArticleCard only uses: `toggle`, `collapse`, `expand`, `loading`, `expanded`, `status`, `html`, `errorMessage`, `isAvailable`, `isError`

### 1.2 Extract Pure Functions
**New functions at file scope:**

```javascript
function markdownToHtml(markdown) {
  if (!markdown) return ''
  try {
    const rawHtml = marked.parse(markdown)
    return DOMPurify.sanitize(rawHtml)
  } catch (error) {
    console.error('Failed to parse markdown:', error)
    return ''
  }
}
```

**Replace IIFE** (lines 37-46):
```javascript
// Before:
const html = (() => {
  if (!markdown) return ''
  try {
    const rawHtml = marked.parse(markdown)
    return DOMPurify.sanitize(rawHtml)
  } catch (error) {
    console.error('Failed to parse markdown:', error)
    return ''
  }
})()

// After:
const html = markdownToHtml(markdown)
```

### 1.3 Simplify Abort/Finally Logic
**Current issue:** The finally block at lines 118-122 has confusing guard logic.

**Current code:**
```javascript
} finally {
  if (!controller.signal.aborted) {
    setLoading(false)
  }
}
```

**Improved approach:**
```javascript
} finally {
  if (!controller.signal.aborted) {
    setLoading(false)
    abortControllerRef.current = null
  }
}
```

**Rationale:** Clear the ref to avoid latent state. The guard prevents clearing loading when THIS fetch was aborted, which is correct - the next fetch will handle it.

### 1.4 Cleanup useEffect
**Add cleanup for abortController:**

```javascript
useEffect(() => {
  return () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    releaseZenLock(url)
  }
}, [url])
```

### Estimated Impact
- Remove ~12 lines (buttonLabel, toggleVisibility)
- Add ~11 lines (pure function)
- Net: -1 line, but significantly clearer

---

## 2. useArticleState.js Refactoring

### 2.1 Remove Dead Code
**Unused by consumers (verified via grep):**
- `state` numeric enum (lines 14-18): Never read by ArticleCard
- `markAsRead()` (lines 35-39): Never called
- `markAsUnread()` (lines 41-45): Never called
- `toggleRead()` (lines 47-50): Destructured but never called
- `setRemoved()` (lines 52-54): Never called (only toggleRemove used)
- `setTldrHidden()` (lines 60-62): Never called (only mark/unmark used)

**Keep (actively used):**
- `isRead`, `isRemoved`, `isTldrHidden` - boolean flags ✓
- `toggleRemove()` - used in ArticleCard ✓
- `markTldrHidden()` - used in ArticleCard ✓
- `unmarkTldrHidden()` - used in ArticleCard ✓
- `updateArticle()` - used by useSummary ✓

### 2.2 Simplified Return Interface
**Before (18 exports):**
```javascript
return {
  article,
  isRead,
  isRemoved,
  isTldrHidden,
  state,
  loading,
  error,
  markAsRead,
  markAsUnread,
  toggleRead,
  setRemoved,
  toggleRemove,
  setTldrHidden,
  markTldrHidden,
  unmarkTldrHidden,
  updateArticle
}
```

**After (10 exports):**
```javascript
return {
  article,
  isRead,
  isRemoved,
  isTldrHidden,
  loading,
  error,
  toggleRemove,
  markTldrHidden,
  unmarkTldrHidden,
  updateArticle
}
```

### Estimated Impact
- Remove ~35 lines (dead code: state computation + 6 unused functions)
- Cleaner, focused API

---

## 3. useLocalStorage.js Refactoring

### 3.1 Remove Journaling Comments
**Lines to remove:**
- Line 4: "State to store our value"
- Line 5: "Pass initial state function to useState so logic only runs once"
- Line 7: "If no key provided, act as a standard non-persistent state"
- Line 16: "Get from local storage by key"
- Line 18: "Parse stored json or if none return initialValue"
- Line 21: "If error also return initialValue"
- Line 27-28: "Return a wrapped version..." comment
- Line 31: "Allow value to be a function..."
- Line 35: "Save state"
- Line 38: "Save to local storage if key exists"
- Line 43: "A more advanced implementation would handle the error case"

### Estimated Impact
- Remove ~11 lines of comments
- Code is self-explanatory without them

---

## Implementation Steps

### Phase 1: Dead Code Removal (Surgical, low-risk)
1. Remove dead exports from useArticleState
2. Remove dead exports from useSummary
3. Update ArticleCard imports if needed (likely no changes needed due to destructuring)

### Phase 2: Pure Function Extraction (Low-risk)
1. Extract `markdownToHtml` in useSummary
2. Replace IIFE with function call

### Phase 3: Logic Improvements (Medium-risk, test carefully)
1. Simplify abort/finally logic in useSummary
2. Enhance cleanup in useEffect

### Phase 4: Comment Cleanup (Zero-risk)
1. Remove journaling comments from useLocalStorage

---

## Verification Strategy

### For each hook:
1. **Grep for consumers** before changes
2. **Run the app** and test affected flows:
   - Fetch TLDR
   - Toggle TLDR visibility
   - Remove article
   - Restore article
   - Collapse TLDR via swipe
3. **Check for new warnings** in console
4. **Verify no regressions** in UI behavior

### Critical test flows:
- **useSummary**: Open TLDR → Close TLDR → Abort fetch → Complete fetch
- **useArticleState**: Remove article → Restore → Toggle TLDR hidden state
- **useLocalStorage**: Fold calendar day → Unfold → Refresh page

---

## Expected Outcomes

### Quantitative:
- **useSummary.js**: 184 → ~173 lines (-11 lines)
- **useArticleState.js**: 90 → ~55 lines (-35 lines)
- **useLocalStorage.js**: 49 → ~38 lines (-11 lines)
- **Total reduction**: ~57 lines

### Qualitative:
- Clearer, more focused APIs
- Self-documenting code (no journaling)
- Simpler abort logic
- No unused exports cluttering the interface
- Easier maintenance (less code to understand)

---

## Files to Modify

1. `/home/user/TLDRScraper/client/src/hooks/useSummary.js`
2. `/home/user/TLDRScraper/client/src/hooks/useArticleState.js`
3. `/home/user/TLDRScraper/client/src/hooks/useLocalStorage.js`

## Files to Verify (consumers)

1. `/home/user/TLDRScraper/client/src/components/ArticleCard.jsx` (primary consumer)
2. Any other components importing these hooks (run grep)

---

## Risk Assessment

**Low Risk:**
- Dead code removal (nothing uses it)
- Comment removal (no behavior change)
- Pure function extraction (same logic, different location)

**Medium Risk:**
- Abort/finally logic change (test thoroughly)
- Cleanup enhancement (test unmount scenarios)

**No Risk:**
- Skipping ARTICLE_STATE constants (not adding unused code)
