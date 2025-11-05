---
last-updated: 2025-11-05 17:22, 72a7115
---

# Headless Browser Testing Tools

This document summarizes the headless browser automation tools available for testing in this project.

## Summary

All three major headless browser automation tools have been successfully installed and tested:

✅ **Playwright** - Already installed, fully functional  
✅ **Selenium** - Available via `uv run --with=selenium`  
✅ **Puppeteer** - Installed and functional

---

## 1. Playwright

**Status:** ✅ Already installed in the project  
**Package:** `@playwright/test` v1.56.1  
**Location:** Root `package.json` devDependencies

### Installation
```bash
# Already installed, but to reinstall:
npm install --save-dev @playwright/test

# Install browsers:
npx playwright install chromium
```

### Usage Example (TypeScript/JavaScript)
```javascript
import { chromium } from '@playwright/test';

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();

await page.goto('https://example.com');
const title = await page.title();
console.log(`Page title: ${title}`);

await browser.close();
```

### Running Tests
```bash
# Run existing Playwright tests
npm run test:e2e

# Or directly with npx
npx playwright test

# Run specific test file
npx playwright test tests/playwright/localStorage.spec.ts
```

### Key Features
- Multi-browser support (Chromium, Firefox, WebKit)
- Excellent TypeScript support
- Built-in test runner and assertions
- Network interception and mocking
- Auto-waiting for elements
- Screenshot and video recording

---

## 2. Selenium

**Status:** ✅ Available via uv  
**Package:** `selenium` (Python)  
**Installation Method:** Ad-hoc via `uv run --with=selenium`

### Installation
No permanent installation needed. Use `uv` for transient usage:

```bash
# Run with Selenium included
source ./setup.sh
uv run --with=selenium python3 your_test.py
```

### Usage Example (Python)
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=chrome_options)

try:
    driver.get('https://example.com')
    title = driver.title
    print(f'Page title: {title}')
    
    h1 = driver.find_element(By.TAG_NAME, 'h1')
    print(f'H1 content: {h1.text}')
finally:
    driver.quit()
```

### Key Features
- Industry standard, widely used
- Multi-language support (Python, Java, JavaScript, C#, Ruby)
- Works with all major browsers
- Grid support for parallel testing
- Mature ecosystem with extensive documentation

---

## 3. Puppeteer

**Status:** ✅ Installed  
**Package:** `puppeteer` (npm)  
**Location:** Root `package.json` devDependencies

### Installation
```bash
# Already installed, but to reinstall:
npm install --save-dev puppeteer
```

### Usage Example (JavaScript/Node.js)
```javascript
import puppeteer from 'puppeteer';

const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
});

const page = await browser.newPage();

try {
    await page.goto('https://example.com', { waitUntil: 'networkidle2' });
    
    const title = await page.title();
    console.log(`Page title: ${title}`);
    
    const h1Text = await page.$eval('h1', el => el.textContent);
    console.log(`H1 content: ${h1Text}`);
} finally {
    await browser.close();
}
```

### Key Features
- Google's official tool for Chrome/Chromium
- High-level API over Chrome DevTools Protocol
- Fast and reliable
- Excellent for Chrome-specific features
- Good for generating PDFs and screenshots
- Performance profiling capabilities

---

## Comparison

| Feature | Playwright | Selenium | Puppeteer |
|---------|-----------|----------|-----------|
| **Multi-browser** | ✅ Chrome, Firefox, WebKit | ✅ All major browsers | ❌ Chrome/Chromium only |
| **Language** | JS/TS, Python, Java, .NET | Python, Java, JS, C#, Ruby | JavaScript/TypeScript |
| **Auto-wait** | ✅ Built-in | ❌ Manual | ⚠️ Some built-in |
| **Speed** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **API Simplicity** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Parallel Testing** | ✅ Built-in | ⚠️ Via Grid | ⚠️ Manual setup |
| **Network Control** | ✅ Excellent | ⚠️ Limited | ✅ Good |
| **Mobile Emulation** | ✅ Yes | ✅ Yes | ✅ Yes |

---

## Recommendations

### Use **Playwright** if:
- You need cross-browser testing
- You want modern features (network interception, auto-waiting)
- You prefer TypeScript/JavaScript
- **Already set up in this project** ✅

### Use **Selenium** if:
- You need Python-based testing
- You're working with existing Selenium tests
- You need specific Selenium Grid features
- Can use ad-hoc via `uv run --with=selenium`

### Use **Puppeteer** if:
- You only need Chrome/Chromium
- You want Chrome-specific features (PDF generation, performance metrics)
- You prefer a simpler API focused on Chrome

---

## Current Project Setup

This project currently uses **Playwright** for E2E testing:
- Tests are in `tests/playwright/`
- Configuration would be in `playwright.config.ts` (if needed)
- Run with `npm run test:e2e`

All three tools are now available for use as needed.
