# Client State Management Tests

## Overview

These tests verify **some of the core state management logic** of the TLDRScraper client without requiring a browser or React environment. They test the pure JavaScript functions that handle localStorage operations and state persistence.

**IMPORTANT LIMITATION:** These tests only verify the extracted logic in isolation. They cannot catch bugs in:
- React component rendering
- DOM manipulation and CSS class toggling
- Component lifecycle (mount/unmount)
- How React reads from localStorage on page load
- Full integration between components

If your app has a bug where removed articles appear after refresh, these tests passing does NOT mean the bug isn't real - the bug may be in the DOM/React layer that these tests don't cover.

## Why These Tests Exist

### The Problem

Full end-to-end browser testing with Playwright can fail in sandboxed environments due to:
- Missing system dependencies (graphics libraries)
- Network restrictions (browser can't access localhost)
- No sudo access for `playwright install-deps`

### The Solution

Extract and test the **actual state management code** - the logic where bugs are most likely to occur:
- localStorage read/write operations
- Cache merge logic
- State persistence across scrapes
- Multiple article state tracking

## What Is Tested

### ✅ Covered by These Tests

1. **Article Removal Persistence**
   - Mark article as removed
   - Re-scrape same date
   - Verify removed state persists

2. **TLDR State Persistence**
   - Fetch TLDR content
   - Re-scrape
   - Verify TLDR cache persists

3. **Read State Persistence**
   - Mark article as read
   - Re-scrape
   - Verify read state persists

4. **Complex Multi-State Scenarios**
   - Multiple articles with different states (removed, read, TLDR, untouched)
   - Re-scrape
   - Verify all states persist correctly

5. **New Articles Handling**
   - Initial scrape with N articles
   - Mark some as removed
   - Re-scrape with N+1 articles
   - Verify: old states persist, new articles appear correctly

### ❌ NOT Covered by These Tests

- React component rendering
- User click handlers
- **DOM manipulation and CSS class toggling** - If state changes should trigger visual changes (e.g., adding `.removed` class), these tests won't catch that
- Visual appearance/layout
- Network requests to Flask API
- Full integration with browser
- **Component mounting/reading from localStorage** - If components fail to read cached state on page load, these tests won't catch it
- **React hooks behavior** - `useState`, `useEffect`, `useCallback` interactions

**⚠️ CRITICAL NOTE:** These uncovered areas CAN and DO contain state bugs. For example:
- A component might correctly save state to localStorage but fail to read it on mount
- State might be correct in localStorage but not reflected in the DOM due to a rendering bug
- CSS classes might not update even though the state changed

These tests passing means the **extracted merge logic works in isolation**. It does NOT guarantee the full app works correctly.

## Running the Tests

### Prerequisites

- Node.js installed (v16+)

### Run

```bash
node tests/client-state/state-management.test.js
```

### Expected Output

```
======================================================================
CLIENT STATE MANAGEMENT TESTS
======================================================================

Test 1: Initial scrape stores articles in localStorage
  ✓ Should have 1 payload
  ✓ Should have 2 articles
  ...
  PASSED

...

======================================================================
TEST SUMMARY
======================================================================
✓ Passed: 24
✗ Failed: 0
Total: 24

🎉 ALL TESTS PASSED! State management logic is working correctly.
```

## How It Works

### 1. localStorage Polyfill

Since Node.js doesn't have `localStorage`, we implement a simple polyfill:

```javascript
class LocalStorage {
  constructor() {
    this.store = new Map()
  }
  getItem(key) { return this.store.get(key) ?? null }
  setItem(key, value) { this.store.set(key, String(value)) }
  // ...
}
global.localStorage = new LocalStorage()
```

### 2. Inline Core Logic

The test file includes the **actual production code** inline (copied from `client/src/lib/scraper.js`):
- `buildDailyPayloadsFromScrape()` - Converts API response to payloads
- `mergeWithCache()` - **The critical function** that merges new scrapes with cached state
- `getNewsletterScrapeKey()` - Storage key generator

This means we're testing **real code**, not a simulation.

### 3. Test Scenarios

Each test:
1. Clears localStorage
2. Simulates a scrape (creates payloads)
3. Simulates user interactions (mark as removed, read, fetch TLDR)
4. Simulates re-scrape
5. Asserts state persists correctly

## Test Cases Explained

### Test 3: The Critical Test 🎯

```javascript
test('Re-scraping same date preserves removed article state', () => {
  // Initial scrape
  const payloads1 = buildDailyPayloadsFromScrape({ articles: [...] })
  mergeWithCache(payloads1)

  // User marks article as removed
  const cached = JSON.parse(localStorage.getItem('newsletters:scrapes:2024-11-01'))
  cached.articles[0].removed = true
  localStorage.setItem('newsletters:scrapes:2024-11-01', JSON.stringify(cached))

  // Server returns fresh scrape (removed=false from API)
  const payloads2 = buildDailyPayloadsFromScrape({ articles: [...] })
  const merged = mergeWithCache(payloads2)

  // CRITICAL: Should still be removed!
  assert(merged[0].articles[0].removed === true)
})
```

**Why This Matters:**
- Server always returns `removed: false` (doesn't track client state)
- Client must preserve user's "removed" choice in cache
- `mergeWithCache()` must prioritize cache over new scrape data
- This test verifies the merge logic is correct

## Adding New Tests

To add a new test:

```javascript
test('Test N: Your test description', () => {
  localStorage.clear()  // Start clean

  // Setup: Initial scrape
  const scrapeData = { articles: [...] }
  const payloads = buildDailyPayloadsFromScrape(scrapeData)
  mergeWithCache(payloads)

  // Action: Simulate user interaction
  const key = 'newsletters:scrapes:2024-11-01'
  const cached = JSON.parse(localStorage.getItem(key))
  // Modify state...
  localStorage.setItem(key, JSON.stringify(cached))

  // Re-scrape
  const newPayloads = buildDailyPayloadsFromScrape({ articles: [...] })
  const merged = mergeWithCache(newPayloads)

  // Assert
  assert(merged[0].articles[0].someProperty === expectedValue, 'Assertion message')
})
```

## Maintenance

### When to Update These Tests

Update when you change:
- `client/src/lib/scraper.js` - Copy updated functions to test file
- `client/src/lib/storageKeys.js` - Update key generator if changed
- localStorage schema - Update test data structures

### Sync Check

Periodically verify the inline code matches source:

```bash
# Compare mergeWithCache implementation
diff <(grep -A 40 "^function mergeWithCache" tests/client-state/state-management.test.js) \
     <(grep -A 40 "^function mergeWithCache" client/src/lib/scraper.js)
```

## Relationship to Other Tests

```
tests/
├── browser-automation/          # Playwright examples (may fail in sandbox)
│   ├── playwright_comprehensive_test.py
│   └── test_localstorage.py
│
├── client-state/                # ✅ WORKS IN SANDBOX
│   ├── state-management.test.js  # This file - production code tests
│   └── README.md                 # This document
│
├── playwright/                  # TypeScript Playwright tests
│   └── localStorage.spec.ts
│
└── unit/                        # Python unit tests
    └── ...
```

**These client-state tests are the most reliable for AI agents testing in restricted environments.**

## Success Criteria

✅ All tests pass (`node tests/client-state/state-management.test.js`)
✅ Tests use actual production code (not mocks/simulations)
✅ Tests cover **some** state persistence scenarios
✅ Tests run without browser/network/sudo requirements
❌ Tests passing does NOT mean the app is bug-free

## See Also

- [Overcoming Sandboxed Playwright Limitations](../../docs/testing/overcoming-sandboxed-playwright-limitations.md)
- [Playwright Capabilities](../../docs/testing/playwright_capabilities_for_tldrscraper.md)
- [Browser Automation Comparison](../../docs/testing/browser-automation-comparison.md)
