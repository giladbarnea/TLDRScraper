---
last_updated: 2025-11-14 16:24, 722a1a0
---
# Manual Browser Testing Guide

## Purpose

This guide documents manual browser testing procedures for the TLDRScraper application, particularly for verifying Supabase storage integration when automated browser testing is unavailable due to environmental constraints.

## When to Use This Guide

- After implementing Phases 4-6 of the Supabase migration
- When automated Playwright tests fail due to environment limitations
- For comprehensive E2E verification before production deployment
- When debugging UI/UX issues related to storage operations

## Prerequisites

1. **Local Development Environment:**
   ```bash
   source ./setup.sh
   start_server_and_watchdog
   cd client && npm run dev
   ```

2. **Browser DevTools:**
   - Chrome DevTools (Cmd/Ctrl + Opt/Alt + I)
   - Network tab for API monitoring
   - Console tab for error checking
   - React DevTools extension (optional but helpful)

3. **Supabase Access:**
   - Supabase Dashboard open in separate tab
   - Access to `daily_cache` and `settings` tables

## Test Suite

### Test 1: Initial App Load

**Objective:** Verify app loads and connects to Supabase storage

**Steps:**
1. Open http://localhost:3000 in browser
2. Open DevTools → Network tab
3. Refresh page (Cmd/Ctrl + R)

**Expected Results:**
- ✅ Page loads without errors
- ✅ Network tab shows requests to `/api/storage/setting/cache:enabled`
- ✅ Console has no error messages
- ✅ React app renders (form visible)

**What's Being Tested:**
- `useSupabaseStorage` hook initialization
- Initial cache setting load from Supabase

---

### Test 2: Cache Toggle

**Objective:** Verify cache setting persists to Supabase

**Steps:**
1. Locate "Cache Enabled" checkbox
2. Note current state (checked/unchecked)
3. Click checkbox to toggle
4. In DevTools Network tab, find POST to `/api/storage/setting/cache:enabled`
5. Refresh page (Cmd/Ctrl + R)

**Expected Results:**
- ✅ Checkbox updates immediately
- ✅ Network shows POST request with new value
- ✅ After refresh, checkbox reflects saved state
- ✅ Supabase Dashboard → `settings` table shows updated row

**What's Being Tested:**
- `useSupabaseStorage` write operations
- Setting persistence across page reloads
- Loading states during async operations

---

### Test 3: Newsletter Scraping (Cache Miss)

**Objective:** Verify scraping and cache storage

**Steps:**
1. In Supabase Dashboard, note current `daily_cache` row count
2. Enter date range (e.g., tomorrow's date)
3. Click "Scrape Newsletters"
4. Watch Network tab for:
   - POST to `/api/scrape`
   - POST to `/api/storage/daily/{date}` (cache save)

**Expected Results:**
- ✅ Scrape button shows "Scraping..." during operation
- ✅ Progress bar visible
- ✅ Results display after completion
- ✅ Articles grouped by date/category
- ✅ Supabase Dashboard shows new `daily_cache` rows
- ✅ Each row has JSONB payload with articles array

**What's Being Tested:**
- `scraper.js` → `storageApi.setDailyPayload`
- Cache write operations
- JSONB structure preservation

---

### Test 4: Newsletter Scraping (Cache Hit)

**Objective:** Verify cache-first behavior

**Steps:**
1. Use same date range from Test 3
2. Click "Scrape Newsletters"
3. Watch Network tab

**Expected Results:**
- ✅ Results load instantly (< 100ms)
- ✅ Network shows GET to `/api/storage/is-cached/{date}`
- ✅ Network shows GET to `/api/storage/daily/{date}`
- ✅ NO POST to `/api/scrape` (cached!)
- ✅ Source badge shows "Cached"

**What's Being Tested:**
- `isRangeCached()` logic
- `loadFromCache()` functionality
- Cache hit performance

---

### Test 5: Mark Article as Read

**Objective:** Verify article state updates persist

**Steps:**
1. Find an unread article (bold blue link)
2. Note article title
3. Click article title link
4. Wait 1 second
5. Observe article appearance changes

**Expected Results:**
- ✅ Link opens in new tab
- ✅ Article link becomes muted gray (not bold)
- ✅ Article moves down in list (below unread articles)
- ✅ Network shows POST to `/api/storage/daily/{date}` with updated payload
- ✅ Refresh page → article still shows as read

**Verify in Supabase Dashboard:**
```sql
SELECT payload->'articles'->0->'read'
FROM daily_cache
WHERE date = '2025-11-13';
-- Should show: {"isRead": true, "markedAt": "2025-11-13T..."}
```

**What's Being Tested:**
- `useArticleState.markAsRead()`
- `useSupabaseStorage` write with loading state
- State persistence
- Re-sorting logic

---

### Test 6: Remove Article

**Objective:** Verify removal state and multiple states coexisting

**Steps:**
1. Hover over any article
2. Click "Remove" button
3. Observe changes
4. Refresh page

**Expected Results:**
- ✅ Button disabled briefly (loading state)
- ✅ Article gets strikethrough + dashed border
- ✅ Article moves to bottom of list
- ✅ Button changes to "Restore"
- ✅ TLDR button hides
- ✅ After refresh, article still removed

**Verify in Supabase Dashboard:**
- Article should have `"removed": true`
- If previously read, `"read": {"isRead": true}` should still exist

**What's Being Tested:**
- `useArticleState.toggleRemove()`
- Loading states (`disabled={loading}`)
- Multiple states coexisting
- CSS class updates

---

### Test 7: Restore Removed Article

**Objective:** Verify state can be toggled back

**Steps:**
1. Find removed article from Test 6
2. Click "Restore" button
3. Observe changes

**Expected Results:**
- ✅ Strikethrough/dashed border removed
- ✅ Article moves up (based on read state)
- ✅ Button changes to "Remove"
- ✅ TLDR button visible again
- ✅ Read state preserved if was read

**What's Being Tested:**
- Toggle functionality
- State independence (removed vs read)

---

### Test 8: Generate TLDR

**Objective:** Verify TLDR generation and storage

**Steps:**
1. Find article with "TLDR" button (not green)
2. Click "TLDR" button
3. Watch button and article changes
4. Refresh page

**Expected Results:**
- ✅ Button shows "Loading..." during API call
- ✅ Button disabled during loading
- ✅ Network shows POST to `/api/tldr-url`
- ✅ After response: TLDR displays inline with markdown formatting
- ✅ Button turns green, shows "Available"
- ✅ Article marked as read automatically
- ✅ After refresh: Button still green, says "Available"

**Verify in Supabase Dashboard:**
```sql
SELECT payload->'articles'->0->'tldr'
FROM daily_cache
WHERE date = '2025-11-13';
-- Should show: {"status": "available", "markdown": "...", ...}
```

**What's Being Tested:**
- `useSummary.fetch()`
- TLDR API integration
- Markdown rendering
- State persistence

---

### Test 9: Hide TLDR

**Objective:** Verify TLDR hidden state

**Steps:**
1. Expand TLDR from Test 8
2. Click "Hide" button
3. Observe changes
4. Refresh page

**Expected Results:**
- ✅ TLDR collapses
- ✅ Article gets 60% opacity + gray background
- ✅ Article moves down (below read articles)
- ✅ Button disabled briefly during save
- ✅ After refresh: Article still has 60% opacity, sorted correctly

**Verify in Supabase Dashboard:**
- Article should have all 3 states:
  - `"tldrHidden": true`
  - `"read": {"isRead": true}`
  - `"tldr": {"status": "available", ...}`

**What's Being Tested:**
- `useArticleState.markTldrHidden()`
- Three states coexisting
- Sorting priority (hidden < read < unread)

---

### Test 10: Expand Hidden TLDR

**Objective:** Verify hidden TLDR can be shown again

**Steps:**
1. Find article with hidden TLDR from Test 9
2. Click TLDR button
3. Observe changes

**Expected Results:**
- ✅ TLDR expands
- ✅ Opacity returns to 100%
- ✅ Gray background removed
- ✅ Article moves up in list (read state, not hidden)
- ✅ Button disabled briefly during save

**What's Being Tested:**
- `useArticleState.unmarkTldrHidden()`
- UI state vs persisted state

---

### Test 11: Article Sorting Verification

**Objective:** Verify correct sort order

**Steps:**
1. Create articles in all 4 states:
   - Unread (don't click link)
   - Read (click link)
   - TLDR-hidden (hide TLDR)
   - Removed (click remove)
2. Observe order from top to bottom
3. Refresh page

**Expected Order:**
```
┌─────────────────────────┐
│ Unread (bold blue)      │
│ Unread                  │
├─────────────────────────┤
│ Read (muted gray)       │
│ Read                    │
├─────────────────────────┤
│ TLDR-hidden (60% opacity│
│ TLDR-hidden             │
├─────────────────────────┤
│ Removed (strikethrough) │
│ Removed                 │
└─────────────────────────┘
```

**What's Being Tested:**
- ArticleList sorting logic
- State priorities: 0 (unread) < 1 (read) < 2 (hidden) < 3 (removed)

---

### Test 12: Error Handling

**Objective:** Verify graceful degradation on errors

**Steps:**
1. Stop Flask backend: `kill_server_and_watchdog`
2. Try to mark article as read
3. Check Console for errors
4. Restart backend: `start_server_and_watchdog`
5. Try action again

**Expected Results:**
- ✅ User-friendly error message displays
- ✅ Article state doesn't change visually
- ✅ Console shows network error (not crash)
- ✅ App remains functional
- ✅ After backend restart, action succeeds

**What's Being Tested:**
- Error handling in `useSupabaseStorage`
- Graceful degradation
- Error states exposed to UI

---

## Checklist for Full Verification

Use this checklist after completing Phases 4-6:

### Core Functionality
- [ ] Initial app load connects to Supabase
- [ ] Cache toggle persists
- [ ] Scraping works (cache miss)
- [ ] Cache-first loading works (cache hit)
- [ ] Mark as read persists
- [ ] Remove article persists
- [ ] Restore article works
- [ ] TLDR generation works
- [ ] Hide TLDR works
- [ ] Expand hidden TLDR works

### State Management
- [ ] All 4 article states work independently
- [ ] Multiple states can coexist
- [ ] States persist across page refresh
- [ ] Sorting reflects state priority correctly

### UX/UI
- [ ] Loading states show (buttons disabled)
- [ ] CSS classes update correctly
- [ ] No console errors during normal operation
- [ ] Error messages display when backend unavailable

### Performance
- [ ] Cache hits load instantly (< 100ms)
- [ ] State updates feel responsive (< 500ms)
- [ ] No unnecessary API calls

---

## Troubleshooting

### Articles Not Sorting Correctly
1. Check ArticleList component re-renders on storage events
2. Verify `supabase-storage-change` event fires
3. Check React DevTools → Components → ArticleList → storageVersion

### States Not Persisting
1. Check Network tab for successful POST requests
2. Verify Supabase Dashboard shows updated data
3. Check for JavaScript errors in Console
4. Verify `useSupabaseStorage` is imported (not `useLocalStorage`)

### Loading States Not Showing
1. Check component uses `loading` from `useArticleState`
2. Verify `disabled={loading}` on buttons
3. Check Network tab for slow responses (may be too fast to see)

### TLDR Not Saving
1. Verify `/api/tldr-url` returns success
2. Check `useSummary` calls `updateArticle` after fetch
3. Verify TLDR structure in Supabase matches expected schema

---

## Browser Testing vs Automated Testing

### Why Manual Testing?

Automated browser testing (Playwright) may fail in certain environments due to:
- Sandboxing restrictions (Chromium as root)
- Missing graphics libraries
- TLS certificate verification issues (ngrok)
- SSH unavailable (localhost.run)

### What Manual Testing Adds

Manual testing verifies:
- Visual appearance (CSS, layout, animations)
- Loading spinner UX
- Button disabled states during async operations
- Real browser performance characteristics
- Copy/paste, keyboard navigation, accessibility

### What Automated Testing Covers

The comprehensive API tests (`test_phase3_api.py`, `test_phase3_e2e_flow.py`) already verify:
- Backend storage integration
- Data persistence
- State management logic
- Error handling
- Multi-state coexistence
- Range queries
- Cache-first behavior

**Conclusion:** Manual browser testing focuses on UX/UI verification, while automated tests ensure functional correctness.

---

## Reporting Issues

When reporting issues found during manual testing, include:

1. **Steps to reproduce**
2. **Expected vs actual behavior**
3. **Screenshots** (especially for UI issues)
4. **Console errors** (copy full stack trace)
5. **Network tab** (screenshot of failed requests)
6. **Supabase data** (SQL query showing unexpected state)

Example:
```
Issue: Article doesn't move when marked as read

Steps:
1. Load app with 5 unread articles
2. Click title of article #3
3. Wait 2 seconds

Expected: Article #3 moves to bottom (position #5)
Actual: Article #3 stays in position #3

Console: No errors
Network: POST /api/storage/daily/2025-11-13 returned 200
Supabase: article.read.isRead = true (correct)

Hypothesis: ArticleList not re-rendering on storage change
```

---

## Next Steps After Manual Testing

If all tests pass:
- ✅ Phase 3 fully verified (hooks + storage)
- ✅ Ready for Phase 4 (scraper.js updates)
- ✅ Ready for Phase 5 (component updates)
- ✅ Ready for Phase 6 (final E2E testing)

If issues found:
- 🔍 Debug using Browser DevTools
- 🔍 Check Supabase Dashboard for data integrity
- 🔍 Review hook implementation
- 🔍 Check event system (`supabase-storage-change`)
