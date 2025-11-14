---
last_updated: 2025-11-14 16:24, 722a1a0
---
# Overcoming Sandboxed Playwright Limitations

## Context

When running in sandboxed environments (like certain CI/CD containers or restricted development environments), Playwright may face limitations:

1. **Missing system dependencies** - Graphics libraries (`libgtk-4.so.1`, `libgraphene-1.0.so.0`, etc.)
2. **Network restrictions** - Browser can't connect to `localhost`
3. **No sudo access** - Can't run `playwright install-deps`

These limitations prevent full end-to-end browser testing against a running local server.

---

## Option 4: Static HTML Snapshot Testing (Hacky But Possible)

### Overview

Create a self-contained HTML file with all JavaScript inlined, load it in Playwright without network requests, and simulate user interactions.

### How It Works

```javascript
// 1. Create standalone HTML file
const html = `
<!DOCTYPE html>
<html>
<head>
  <title>TLDRScraper Test Snapshot</title>
  <script>
    // Inline your entire state management logic here
    const scraper = {
      scrapeNewsletters: async (start, end) => { /* ... */ },
      mergeWithCache: (payloads) => { /* ... */ },
      // All localStorage operations
    };

    // Mock fetch to return test data
    window.fetch = async (url, options) => {
      if (url === '/api/scrape') {
        return {
          ok: true,
          json: async () => ({
            success: true,
            newsletters: [
              {title: 'Test Article', url: 'example.com', date: '2024-11-01'}
            ]
          })
        };
      }
    };
  </script>
</head>
<body>
  <form id="scrapeForm">
    <input id="start_date" type="date" />
    <input id="end_date" type="date" />
    <button id="scrapeBtn">Scrape</button>
  </form>
  <div class="results-container"></div>

  <script>
    // Your React-like rendering logic manually recreated
    document.getElementById('scrapeBtn').addEventListener('click', async () => {
      const start = document.getElementById('start_date').value;
      const results = await scraper.scrapeNewsletters(start, start);
      // Render results...
    });
  </script>
</body>
</html>
`;

// 2. Load in Playwright (no network needed)
page.setContent(html);

// 3. Interact and test
await page.fill('#start_date', '2024-11-01');
await page.click('#scrapeBtn');
await page.waitForSelector('.article-card');

// 4. Test localStorage
const cache = await page.evaluate(() => {
  return JSON.parse(localStorage.getItem('newsletters:scrapes:2024-11-01'));
});
expect(cache.newsletters).toHaveLength(1);
```

### Pros

- ✅ Works in sandboxed environments (no network, no external deps)
- ✅ Can test localStorage operations
- ✅ Can test DOM manipulation and state changes
- ✅ Playwright's full API available

### Cons

- ❌ **Not testing real code** - Must manually recreate app logic
- ❌ **Extremely brittle** - Breaks when real app changes
- ❌ **High maintenance** - Two codebases (real app + test snapshot)
- ❌ **Divergence risk** - Test snapshot may not match real behavior
- ❌ **No React testing** - Must reimplement React's behavior
- ❌ **Mock everything** - Fetch, routing, state management
- ❌ **Untrustworthy** - Testing a simulation, not reality

### When To Use

**Only use this approach when:**

1. You MUST have some form of browser testing in a sandboxed environment
2. You can't extract state logic for unit testing (Option 3)
3. You understand the maintenance burden
4. You accept the risk of test/implementation divergence

**Better alternatives:**

- **Option 3**: Extract state management logic and unit test it (no browser needed)
- **Local testing**: Run full Playwright tests on your machine or CI with proper deps
- **API testing**: Test the backend directly with `requests`/`curl`

---

## Implementation Example

### Step 1: Create Snapshot HTML

```javascript
// tests/browser-automation/snapshots/create-snapshot.js
import fs from 'fs';
import path from 'path';

// Read your actual client code
const scraperLogic = fs.readFileSync('client/src/lib/scraper.js', 'utf8');
const storageKeys = fs.readFileSync('client/src/lib/storageKeys.js', 'utf8');

// Create standalone HTML
const snapshot = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>TLDRScraper Snapshot Test</title>
  <style>
    /* Inline your CSS */
    .article-card { border: 1px solid #ccc; padding: 10px; }
    .removed { opacity: 0.5; }
  </style>
</head>
<body>
  <div id="root">
    <!-- Your app structure -->
  </div>

  <script>
    // Inline state management
    ${scraperLogic}
    ${storageKeys}

    // Mock fetch
    window.fetch = async (url, options) => {
      // Return test data
    };

    // Simple rendering (not real React)
    function render() {
      // DOM manipulation
    }
  </script>
</body>
</html>
`;

fs.writeFileSync('tests/browser-automation/snapshots/app-snapshot.html', snapshot);
```

### Step 2: Test Against Snapshot

```javascript
// tests/browser-automation/snapshot.test.js
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

test('remove article persists after re-scrape', async ({ page }) => {
  // Load snapshot (no network)
  const html = fs.readFileSync(
    path.join(__dirname, 'snapshots/app-snapshot.html'),
    'utf8'
  );
  await page.setContent(html);

  // Clear localStorage
  await page.evaluate(() => localStorage.clear());

  // Simulate scrape
  await page.fill('#start_date', '2024-11-01');
  await page.click('#scrapeBtn');
  await page.waitForSelector('.article-card');

  // Click remove on first article
  await page.locator('.article-card').first().locator('.remove-article-btn').click();

  // Verify removed class
  const classes = await page.locator('.article-card').first().getAttribute('class');
  expect(classes).toContain('removed');

  // Verify localStorage updated
  const cache = await page.evaluate(() => {
    return JSON.parse(localStorage.getItem('newsletters:scrapes:2024-11-01'));
  });
  expect(cache.newsletters[0].removed).toBe(true);

  // Simulate re-scrape
  await page.click('#scrapeBtn');
  await page.waitForTimeout(500);

  // Assert: Article still removed
  const classesAfter = await page.locator('.article-card').first().getAttribute('class');
  expect(classesAfter).toContain('removed');
});
```

---

## Maintenance Strategy

If you must use this approach:

1. **Keep snapshots in sync**
   - Run snapshot generation in pre-commit hook
   - Compare snapshot hash to detect drift

2. **Version snapshots**
   - `app-snapshot-v1.0.0.html`
   - Update when breaking changes occur

3. **Limit scope**
   - Only snapshot critical flows
   - Don't try to snapshot entire app

4. **Automated validation**
   - Script to compare snapshot behavior vs real app
   - Run on CI where full Playwright works

---

## Why This Is Labeled "Hacky"

**The fundamental problem:** You're maintaining two implementations:
1. Your real React app
2. A simplified version in the snapshot

Every time your app changes, the snapshot diverges. You're now testing a simulation that may not match reality.

**Example divergence:**
```javascript
// Real app (client/src/lib/scraper.js)
function mergeWithCache(payloads) {
  return payloads.map(payload => {
    const cached = localStorage.getItem(getKey(payload.date));
    // Complex merge logic with bug fix
    return deepMerge(payload, cached, { preserveRemoved: true });
  });
}

// Snapshot (simplified, might miss the bug)
function mergeWithCache(payloads) {
  return payloads.map(payload => {
    const cached = localStorage.getItem(getKey(payload.date));
    return { ...cached, ...payload }; // Naive merge, different behavior!
  });
}
```

The snapshot test passes ✅, but the real app has a bug 🐛.

---

## Conclusion

**Static HTML Snapshot Testing is possible but not recommended.**

- ✅ Works around sandboxed environment limitations
- ❌ Untrustworthy (tests a simulation, not reality)
- ❌ High maintenance burden
- ❌ Risk of test/implementation divergence

**Better approach:** Option 3 - Extract and unit test state management logic directly with Node.js and localStorage polyfill. Tests real code, no browser needed.

---

## See Also

- [Playwright Capabilities](./playwright_capabilities_for_tldrscraper.md)
- [Browser Automation Comparison](./browser-automation-comparison.md)
- Unit testing state logic: `tests/client-state/` (Option 3 implementation)
