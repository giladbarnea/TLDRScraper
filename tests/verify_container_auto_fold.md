---
last_updated: 2025-11-26 19:54, cbcd0ca
---
# Container Auto-Fold Verification

## What Changed
Added real-time auto-fold detection to `FoldableContainer.jsx` that triggers when all child articles are removed.

## Implementation
The component now uses a `useEffect` hook that:
1. Tracks the previous value of `defaultFolded` using a ref
2. Detects when `defaultFolded` transitions from `false` → `true`
3. Automatically calls `setIsFolded(true)` when this transition occurs
4. Is idempotent - safe to call multiple times

## Manual Verification Steps

### Test 1: Section auto-fold
1. Scrape newsletters for a date range
2. Find a section with 2+ articles
3. Remove all articles except one
4. **Verify**: Section remains unfolded
5. Remove the last article
6. **Expected**: Section should immediately auto-fold (no refresh needed)

### Test 2: Newsletter auto-fold
1. Find a newsletter with multiple sections
2. Remove all articles from all sections
3. **Expected**: Newsletter container should auto-fold immediately

### Test 3: Calendar day auto-fold
1. Find a date with multiple newsletters
2. Remove all articles from all newsletters
3. **Expected**: Calendar day should auto-fold immediately

### Test 4: Manual unfold still works
1. Find a fully-removed container (auto-folded)
2. Manually click to unfold it
3. **Expected**: Container unfolds and stays unfolded (until next remove action)

## Edge Cases Covered
- ✅ Idempotent: Calling `setIsFolded(true)` when already folded is safe
- ✅ Transition-based: Only auto-folds on state change, not on every render
- ✅ User override: Manual unfolds are respected (until next transition)
- ✅ Applies to all levels: CalendarDay, NewsletterDay, and Section containers
