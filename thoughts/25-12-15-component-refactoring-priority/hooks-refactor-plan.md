---
last_updated: 2025-12-21 08:04, 4b3987f
---
# Hooks Refactoring Plan

Following the same design patterns applied in the component refactoring (preplan.md), this plan addresses `client/src/hooks/`.

---

## North-Star Patterns (From Component Refactoring)

The component refactoring established these patterns:

1. **Pure functions at file scope**: Data transformations, computations, and helpers extracted outside components/hooks
2. **MECE sub-units**: Each unit does one thing clearly
3. **Derived state computed declaratively**: No IIFE or inline computation in render/hook body
4. **Clean return interfaces**: Logical groupings where needed
5. **No journaling comments**: Code should be self-documenting

---

## Hook-by-Hook Analysis

### 1. useSummary.js (184 lines) - HIGH Priority

**Current Issues:**

1. **IIFE for markdown-to-html conversion** (lines 37-46): The `html` derived value uses an immediately-invoked function expression inside the hook body. This should be a pure function at file scope.

2. **Duplicate toggle logic**: `toggle()` and `toggleVisibility()` share nearly identical zen lock acquire/release patterns (lines 125-158). These should be consolidated.

3. **Inline buttonLabel computation** (lines 53-57): Derived state computed inline. Should be extracted as a pure function.

4. **Large flat return object** (18 properties): Could benefit from logical grouping but not strictly necessary.

**Proposed Changes:**

```javascript
// Extract to file scope:
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

function computeButtonLabel(isLoading, expanded, isAvailable, isError) {
  if (isLoading) return 'Loading...'
  if (expanded) return 'Hide'
  if (isAvailable) return 'Available'
  if (isError) return 'Retry'
  return 'TLDR'
}

// Consolidate toggle functions - toggleVisibility() is a subset of toggle()
// Remove toggleVisibility() and have consumers use toggle() directly
```

**Estimated reduction:** ~20 lines

---

### 2. useArticleState.js (90 lines) - MEDIUM Priority

**Current Issues:**

1. **Magic numbers in state derivation** (lines 14-18): The numeric state (0, 1, 2, 3) is opaque. Should use named constants.

2. **Redundant action pairs**: Several functions exist as pairs that could be consolidated:
   - `markAsRead()` / `markAsUnread()` / `toggleRead()`
   - `setRemoved()` / `toggleRemove()`
   - `setTldrHidden()` / `markTldrHidden()` / `unmarkTldrHidden()`

   The "mark/unmark" variants are thin wrappers around "set" - consider whether both are needed.

**Proposed Changes:**

```javascript
// Extract to file scope:
const ARTICLE_STATE = {
  UNREAD: 0,
  READ: 1,
  TLDR_HIDDEN: 2,
  REMOVED: 3
}

function deriveArticleState(article) {
  if (!article) return ARTICLE_STATE.UNREAD
  if (article.removed) return ARTICLE_STATE.REMOVED
  if (article.tldrHidden) return ARTICLE_STATE.TLDR_HIDDEN
  if (article.read?.isRead) return ARTICLE_STATE.READ
  return ARTICLE_STATE.UNREAD
}
```

**Action cleanup:** Remove `markTldrHidden()` and `unmarkTldrHidden()` - consumers can use `setTldrHidden(true/false)` directly. Same for `markAsRead()`/`markAsUnread()` if `toggleRead()` suffices.

**Estimated reduction:** ~10 lines

---

### 3. useLocalStorage.js (49 lines) - LOW Priority

**Current Issues:**

1. **Journaling comments throughout**: "State to store our value", "Pass initial state function...", "Return a wrapped version...", "A more advanced implementation would handle..." - all violate project conventions.

**Proposed Changes:**

Remove all comments. The code is self-explanatory.

**Estimated reduction:** ~8 lines

---

### 4. useSupabaseStorage.js (222 lines) - LOW Priority

**Assessment:** Already well-structured.

- Module-level caches and listeners properly extracted
- Pure functions (`emitChange`, `subscribe`, `readValue`, `writeValue`) at file scope
- biome-ignore comments explain intentional dependency omissions

**No significant refactoring needed.**

---

### 5. useScrollProgress.js (23 lines) - MINIMAL

**Assessment:** Clean and simple.

- Could extract `calculateProgress` but gains are minimal for 5 lines of logic.

**No refactoring needed.**

---

### 6. useSwipeToRemove.js (59 lines) - MINIMAL

**Assessment:** Well-contained.

- Animation thresholds could be constants but it's fine as-is.

**No refactoring needed.**

---

## Implementation Order

1. **useSummary.js** - Largest gains, highest complexity
2. **useArticleState.js** - Medium gains, clearer state semantics
3. **useLocalStorage.js** - Quick cleanup

Total estimated line reduction: ~38 lines

---

## Verification Strategy

For each hook refactored:

1. Ensure all consuming components still work (grep for imports)
2. Test the affected UI flows manually
3. No new eslint/biome warnings

---

## Questions for Review

1. **toggleVisibility() removal**: The function appears redundant with `toggle()` - both manage zen lock acquisition. Should consumers always use `toggle()`? Need to check ArticleCard.jsx usage.

2. **State constants export**: Should `ARTICLE_STATE` be exported for consumers, or kept internal?

3. **Action function consolidation**: How aggressively should we remove convenience wrappers like `markAsRead()`? Trade-off is API simplicity vs. explicit intent in consuming code.
