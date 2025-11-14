---
last_updated: 2025-11-14 16:24, 722a1a0
---
# Code Duplication Refactoring Plan

## Executive Summary

**Issue B**: Storage key pattern `newsletters:scrapes:${date}` scattered across 6 locations in 4 files.

This issue can be resolved with straightforward refactoring that reduces complexity and maintenance burden without over-engineering.

## Issue B: localStorage Key Pattern Scattered Everywhere

### Problem Analysis

**Location**: `/home/user/TLDRScraper/client/src/`

The pattern `newsletters:scrapes:${date}` appears in **6 locations across 4 files**:
1. `lib/scraper.js` - lines 52, 126, 167 (3 occurrences)
2. `hooks/useArticleState.js` - line 5 (1 occurrence)
3. `components/ArticleList.jsx` - line 18 (1 occurrence)
4. `components/ResultsDisplay.jsx` - line 45 (1 occurrence)

**Impact**:
- Changing the key format requires updating 6 locations
- Risk of typos causing bugs
- No single source of truth

### Solution

Create a storage key utility that centralizes the pattern.

**File**: Create `/home/user/TLDRScraper/client/src/lib/storageKeys.js`

```javascript
/**
 * Centralized storage key patterns for localStorage
 */

export const STORAGE_KEYS = {
  CACHE_ENABLED: 'cache:enabled'
}

export function getNewsletterScrapeKey(date) {
  return `newsletters:scrapes:${date}`
}
```

**Implementation steps**:
1. Create `client/src/lib/storageKeys.js` with the utility function
2. Update all 6 locations to import and use `getNewsletterScrapeKey(date)`
3. Verify no regressions with manual testing

**Files to update**:
- `client/src/lib/scraper.js` (3 replacements)
- `client/src/hooks/useArticleState.js` (1 replacement)
- `client/src/components/ArticleList.jsx` (1 replacement)
- `client/src/components/ResultsDisplay.jsx` (1 replacement)

**Example replacement**:
```javascript
// Before
const key = `newsletters:scrapes:${date}`

// After
import { getNewsletterScrapeKey } from '../lib/storageKeys'
const key = getNewsletterScrapeKey(date)
```

**Benefits**:
- Single source of truth
- Easier to change format in future
- Reduces risk of typos/inconsistencies
- Better discoverability (all storage keys in one place)

**Risks**: None. Simple string replacement.


## Implementation Plan

**Why first**: Simplest change, pure string replacement, no logic changes.

1. Create `client/src/lib/storageKeys.js`
2. Update 6 import statements and 6 call sites
3. Test manually (scrape, check localStorage, verify cache works)

## Testing Strategy

### Manual Testing Checklist

- [ ] Run scrape with cache enabled
- [ ] Verify localStorage contains keys with correct pattern
- [ ] Check all components can read/write cached data
- [ ] Verify article state updates persist correctly


- **Issue A**: If section parsing breaks, revert `tldr_adapter.py` to previous version
- **Issue B**: If storage breaks, revert all 6 files and `storageKeys.js`

## Opportunities

**Add TypeScript types**: Consider adding JSDoc types to `storageKeys.js` for better IDE support  // this is a good idea. do it

