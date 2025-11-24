# Playwright in Sandboxed Environment: What Works and What Doesn't

## Testing Environment
- Headless Chromium with sandbox flags: `--no-sandbox`, `--disable-setuid-sandbox`, `--disable-dev-shm-usage`, etc.
- Target: localhost React application
- Python Playwright sync API

---

## ✅ Features That WORK (20/22 tested)

### Core Debugging & Inspection
1. **`page.evaluate()`** - JavaScript execution in browser context
   - Get DOM properties, computed styles, localStorage
   - Modify page state
   - Query selectors and element properties

2. **`page.on("console")`** - Console message monitoring
   - Captures `console.log`, `console.error`, etc.

3. **`page.on("pageerror")`** - JavaScript error monitoring
   - Catches uncaught exceptions

4. **`page.on("request")`/`page.on("response")`** - Network monitoring
   - Track all HTTP requests/responses

5. **`page.route()`** - Network interception
   - Mock API responses with `route.fulfill()`
   - Modify requests with `route.continue_()`

6. **`page.expect_response()`** - Wait for specific network requests
   - Useful for API testing

### Screenshots
7. **`page.screenshot()`** - Full page screenshots ✅
   - Successfully creates PNG files

8. **`locator.screenshot()`** - Element screenshots ✅
   - Captures specific elements

### Form Interactions
9. **`locator.fill()`** - Fill input fields
   - Works with text inputs, date inputs, etc.

10. **`page.type()`** - Type text character by character
    - Simulates keyboard typing

11. **`page.keyboard.press()`** - Keyboard events
    - Tab, Enter, Control+A, etc.

### Element Interactions
12. **`locator.click(force=True)`** - Force click elements ✅
    - **Note**: Regular `.click()` fails when overlays intercept pointer events
    - Use `force=True` parameter to bypass overlay issues

13. **`locator.hover()`** - Hover over elements

### Element Inspection
14. **`locator.bounding_box()`** - Get element position and dimensions
    - Returns `{x, y, width, height}`

15. **`locator.get_attribute()`** - Get HTML attributes
    - class, id, aria-label, etc.

16. **`locator.input_value()`** - Get input field values

17. **`page.wait_for_selector()`** - Wait for elements to appear

### localStorage Access
18. **Full localStorage control via `page.evaluate()`**
    ```python
    # Set
    page.evaluate("() => localStorage.setItem('key', 'value')")
    # Get
    value = page.evaluate("() => localStorage.getItem('key')")
    # Clear
    page.evaluate("() => localStorage.clear()")
    ```

### Advanced Features
19. **Multiple browser contexts** - Isolated sessions
    - Each context has separate localStorage, cookies, cache

20. **`window.getComputedStyle()` via page.evaluate()**
    - Get actual rendered CSS properties (opacity, backgroundColor, position, etc.)

---

## ❌ Features That FAIL or Are Unreliable

### 1. **Regular `.click()` - Fails with overlays** ❌
**Problem**: Elements intercepted by overlays (sticky headers, modals, etc.)

**Error**:
```
Locator.click: Timeout 30000ms exceeded
<header>intercepts pointer events
```

**Solution**: Use `.click(force=True)` instead

**Doc Location**: `docs/testing/playwright_capabilities_for_tldrscraper.md` lines 102-108

### 2. **Video Recording** ❌
**Problem**: No video file created despite API accepting the parameter

**Test**:
```python
context = browser.new_context(record_video_dir="/tmp/videos")
```

**Result**: Directory created but remains empty

**Doc Location**: `docs/testing/playwright_capabilities_for_tldrscraper.md` lines 225-227

### 3. **Drag and Drop** ❌ (Causes Browser Crash)
**Problem**: `page.drag_and_drop()` causes "Target crashed" error

**Error**:
```
Locator.bounding_box: Target crashed
```

**Doc Location**: `docs/testing/playwright_capabilities_for_tldrscraper.md` lines 272-273

**Note**: This may work for specific draggable elements, but unreliable in general

---

## Key Insights for AI Agents

### What Worked for Debugging
I successfully used Playwright as a **JavaScript execution and inspection tool** rather than a full browser automation framework:

1. **JavaScript execution** (`page.evaluate()`) for all inspection:
   - DOM queries
   - Style inspection
   - localStorage access
   - Custom diagnostics

2. **Event listeners** for monitoring:
   - Console logs
   - Page errors
   - Network requests

3. **Simple waits**: `time.sleep()` + `wait_until="domcontentloaded"` instead of complex network idle waits

4. **Screenshots** for visual confirmation (they work!)

### What to Avoid
1. **Complex click interactions** - overlays cause failures
   - Use `force=True` parameter
   - Or use `page.evaluate()` to trigger click events via JavaScript

2. **Video recording** - doesn't work in sandboxed environment

3. **Drag and drop** - causes crashes

4. **Visual regression testing** - not tested, but likely problematic without stable rendering

5. **External URLs** - network restrictions may block (Google Fonts failed)

---

## Recommendations for Documentation Updates

### `docs/testing/playwright_capabilities_for_tldrscraper.md`

#### Issues Found:

1. **Line 102-108**: Click examples should mention overlay interception issue
   ```python
   # ❌ FAILS with overlays
   first_article.locator(".remove-article-btn").click()

   # ✅ WORKS
   first_article.locator(".remove-article-btn").click(force=True)
   ```

2. **Lines 225-227**: Video recording example should note it doesn't work in sandboxed environments
   ```python
   # Record video (doesn't work in sandboxed environments)
   context = browser.new_context(record_video_dir="/tmp/videos")  # ❌ No video created
   ```

3. **Lines 272-273**: Drag and drop example should warn about browser crashes
   ```python
   # Drag and drop (may cause crashes in sandboxed environments)
   page.drag_and_drop(".source", ".target")  # ❌ Target crashed
   ```

4. **Missing**: Document that `page.evaluate()` is the most reliable approach for sandboxed environments

---

## Success Rate: 20/22 (91%)

The vast majority of Playwright features work perfectly in sandboxed environments when used correctly. The key is treating it as a JavaScript execution and monitoring tool rather than relying on complex pointer interactions or video features.
