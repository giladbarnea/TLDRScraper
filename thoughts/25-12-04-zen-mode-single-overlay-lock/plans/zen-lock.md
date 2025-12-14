---
created: 2025-12-14 17:15
last_updated: 2025-12-14 17:19, 0976753
---
# Zen Mode Single Overlay Lock - Implementation Plan

## Overview

Prevent multiple zen mode overlays from stacking when multiple TLDR requests complete while user is viewing an expanded modal. Implement a module-level lock that allows at most one modal open at a time.

## Current State Analysis

- `ZenModeOverlay` renders when `tldr.expanded && tldr.html` is true (`ArticleCard.jsx:253`)
- Each `ArticleCard` has independent `expanded` state via `useSummary` hook (`useSummary.js:13`)
- On fetch success, `setExpanded(true)` is called immediately (`useSummary.js:80`)
- **Problem**: Multiple ArticleCards can have `expanded=true` simultaneously

### Key Discoveries:
- Lock should live at module level in `useSummary.js` (follows `useSupabaseStorage.js:3-5` pattern)
- Three places set `expanded=true`: lines 80, 109, 120
- One place sets `expanded=false`: `collapse()` at line 116
- Full-screen modal blocks interaction, making stuck locks unlikely but worth guarding against

## Desired End State

- At most one zen modal visible at any time
- TLDR requests that complete while another modal is open: content is cached, no modal opens
- User can view cached TLDR by tapping article again after closing current modal
- Lock released when modal closes (user action) or component unmounts (edge case)

**Verification**: Open two TLDR requests in quick succession. First to complete opens modal. Second completes silently (cached). Close first modal, tap second article - modal opens immediately from cache.

## What We're NOT Doing

- No queuing system for pending modals
- No visual indicator that a TLDR completed while another modal was open
- No changes to caching behavior (already works correctly)
- No changes to `ZenModeOverlay` component itself

## Implementation Approach

Add a URL-based lock mechanism to `useSummary.js`. The lock owner is identified by article URL to enable proper release on unmount.

## Phase 1: Add Lock Mechanism

### Overview
Add module-level lock state and acquire/release functions to `useSummary.js`.

### Changes Required:

#### 1. Add lock state and functions
**File**: `client/src/hooks/useSummary.js`
**Location**: After imports, before the `useSummary` function (around line 5)

```javascript
let zenLockOwner = null

function acquireZenLock(url) {
  if (zenLockOwner === null) {
    zenLockOwner = url
    return true
  }
  return false
}

function releaseZenLock(url) {
  if (zenLockOwner === url) {
    zenLockOwner = null
  }
}
```

#### 2. Gate `setExpanded(true)` on lock acquisition
**File**: `client/src/hooks/useSummary.js`

**Change 1** - In `fetchTldr` success handler (line 80):
```javascript
// Before:
setExpanded(true)

// After:
if (acquireZenLock(url)) {
  setExpanded(true)
}
```

**Change 2** - In `toggle` function (line 109):
```javascript
// Before:
setExpanded(!expanded)

// After:
if (expanded) {
  releaseZenLock(url)
  setExpanded(false)
} else if (acquireZenLock(url)) {
  setExpanded(true)
}
```

**Change 3** - In `expand` function (line 120):
```javascript
// Before:
setExpanded(true)

// After:
if (acquireZenLock(url)) {
  setExpanded(true)
}
```

**Change 4** - In `toggleVisibility` function (line 125):
```javascript
// Before:
setExpanded(!expanded)

// After:
if (expanded) {
  releaseZenLock(url)
  setExpanded(false)
} else if (acquireZenLock(url)) {
  setExpanded(true)
}
```

#### 3. Release lock in `collapse`
**File**: `client/src/hooks/useSummary.js`

```javascript
// Before:
const collapse = () => {
  setExpanded(false)
}

// After:
const collapse = () => {
  releaseZenLock(url)
  setExpanded(false)
}
```

#### 4. Add cleanup on unmount
**File**: `client/src/hooks/useSummary.js`
**Location**: Inside `useSummary` function, add a `useEffect`

```javascript
useEffect(() => {
  return () => {
    // Will not happen in practice but guards against future UI changes
    releaseZenLock(url)
  }
}, [url])
```

**Note**: Add `useEffect` to the import from 'react' at line 3.

### Success Criteria:

#### Automated Verification:
- [ ] No syntax/import errors: `cd client && npm run build`
- [ ] TypeScript/ESLint passes: `cd client && npm run lint`

#### Manual Verification:
- [ ] Single modal behavior: Tap article A, modal opens. Tap article B (while A's modal open) - nothing happens (B blocked by full-screen modal, but if it somehow triggered, lock prevents second modal)
- [ ] Lock release on close: Open modal, close it, open different article's TLDR - works
- [ ] Concurrent requests: Tap article A (uncached), quickly tap article B (uncached). First to complete opens modal. Close it. Tap the other - opens immediately from cache.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding.

---

## Testing Strategy

### Unit Tests:
None required - lock is simple module state. Covered by manual testing.

### Integration Tests:
Could add Playwright test but manual verification sufficient for this scope.

### Manual Testing Steps:
1. Start fresh (no cached TLDRs)
2. Tap article A - loading starts
3. While loading, tap article B - loading starts
4. First completion opens modal
5. Second completion: no second modal appears
6. Close modal
7. Tap the article that completed second - modal opens immediately (was cached)
8. Verify scroll, close button, escape key all work normally

## References

- Preplan: `thoughts/25-12-04-zen-mode-single-overlay-lock/preplan.md`
- Module-level state pattern: `client/src/hooks/useSupabaseStorage.js:3-5`
- Current implementation: `client/src/hooks/useSummary.js`
