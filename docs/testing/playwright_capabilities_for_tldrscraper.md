---
last-updated: 2025-11-05 17:46, b247968
---

# Playwright Capabilities for TLDRScraper Testing

## YES to Everything You Asked! ✅

Playwright can absolutely do **all** of the following:

---

## 1. ✅ Scraping & Waiting for Results

```python
# Fill form
page.fill("#start_date", "2024-11-01")
page.fill("#end_date", "2024-11-01")

# Click scrape
page.click("#scrapeBtn")

# Wait for completion (smart waiting!)
page.wait_for_selector("button:has-text('Scrape Newsletters')", timeout=30000)

# Verify results appeared
articles = page.locator(".article-card")
assert articles.count() > 0
```

---

## 2. ✅ Pressing TLDR & Waiting for Content

```python
# Find TLDR button in first article
first_article = page.locator(".article-card").first
tldr_button = first_article.locator(".tldr-btn")

# Click TLDR
tldr_button.click()

# Wait for TLDR content to appear
tldr_content = first_article.locator(".inline-tldr")
tldr_content.wait_for(timeout=30000)

# Verify it's visible
assert tldr_content.is_visible()
```

---

## 3. ✅ Asserting Content is Displayed

```python
# Check visibility
assert page.locator(".results-container").is_visible()

# Get text content
tldr_text = tldr_content.text_content()
assert len(tldr_text) > 0, "TLDR is empty!"

# Check specific text
expect(page.locator(".inline-tldr")).to_contain_text("TLDR")

# Count elements
article_count = page.locator(".article-card").count()
print(f"Found {article_count} articles")

# Check HTML
html = page.locator(".inline-tldr").inner_html()
assert "<div>" in html
```

---

## 4. ✅ Pressing Remove & Verifying Style/Position Changes

```python
# Get baseline state
first_article = page.locator(".article-card").first

# Get position BEFORE removal
bbox_before = first_article.bounding_box()
# Returns: {'x': 100, 'y': 200, 'width': 800, 'height': 150}

# Get computed styles BEFORE removal
styles_before = first_article.evaluate("""
    (element) => {
        const computed = window.getComputedStyle(element)
        return {
            opacity: computed.opacity,
            backgroundColor: computed.backgroundColor,
            height: computed.height,
            order: computed.order
        }
    }
""")
# Returns: {'opacity': '1', 'backgroundColor': 'rgb(255, 255, 255)', ...}

# Click Remove button
first_article.locator(".remove-article-btn").click()

# Wait for state change
page.wait_for_timeout(500)  # Or wait for class change

# Get classes AFTER removal
classes_after = first_article.get_attribute("class")
assert "removed" in classes_after

# Get styles AFTER removal
styles_after = first_article.evaluate("""
    (element) => {
        const computed = window.getComputedStyle(element)
        return {
            opacity: computed.opacity,
            backgroundColor: computed.backgroundColor,
            height: computed.height,
            order: computed.order
        }
    }
""")

# Assert style changed
assert styles_before['opacity'] != styles_after['opacity']
print(f"Opacity: {styles_before['opacity']} → {styles_after['opacity']}")

# Get position AFTER removal
bbox_after = first_article.bounding_box()

# Assert position changed (moved to bottom if removed articles reorder)
if bbox_before['y'] != bbox_after['y']:
    print(f"Position changed: y={bbox_before['y']} → y={bbox_after['y']}")

# Verify button text changed
button_text = first_article.locator(".remove-article-btn").text_content()
assert button_text == "Restore"
```

---

## 5. ✅ Testing localStorage (clientStorage) - THIS IS HUGE!

### Playwright has FULL access to localStorage!

```python
# Clear localStorage
page.evaluate("() => localStorage.clear()")

# Set items
page.evaluate("""
    () => {
        localStorage.setItem('test-key', 'test-value')
        localStorage.setItem('cache-enabled', 'true')
    }
""")

# Get items
value = page.evaluate("() => localStorage.getItem('test-key')")
# Returns: "test-value"

# Get all keys
all_keys = page.evaluate("""
    () => {
        const keys = []
        for (let i = 0; i < localStorage.length; i++) {
            keys.push(localStorage.key(i))
        }
        return keys
    }
""")
# Returns: ['test-key', 'cache-enabled', 'newsletters:scrapes:2024-11-01']

# Pre-seed localStorage with test data!
page.evaluate("""
    (testData) => {
        localStorage.setItem('newsletters:scrapes:2024-11-01', JSON.stringify(testData))
    }
""", {
    "date": "2024-11-01",
    "newsletters": [
        {"title": "Test Article", "url": "example.com", "removed": False}
    ]
})

# Get specific newsletter cache
newsletter_data = page.evaluate("""
    () => {
        const key = 'newsletters:scrapes:2024-11-01'
        return JSON.parse(localStorage.getItem(key) || '{}')
    }
""")
# Returns: Python dict with newsletter data

# Verify article removal state in localStorage
article_url = "https://example.com"
is_removed = page.evaluate(f"""
    (url) => {{
        const data = JSON.parse(localStorage.getItem('newsletters:scrapes:2024-11-01') || '{{}}')
        const article = data.newsletters?.find(n => n.url.includes(url))
        return article?.removed || false
    }}
""", article_url)
# Returns: True/False

# Dump entire localStorage as JSON
full_storage = page.evaluate("() => JSON.stringify(localStorage)")
# Returns: JSON string of entire localStorage

# Check if key exists
has_cache = page.evaluate("() => localStorage.getItem('cache-enabled') !== null")
# Returns: True/False
```

---

## Advanced Capabilities You Didn't Ask About (But Are Awesome!)

### Screenshots & Videos
```python
# Take screenshot
page.screenshot(path="/tmp/screenshot.png")

# Screenshot specific element
first_article.screenshot(path="/tmp/article.png")

# Record video (set at browser launch)
context = browser.new_context(record_video_dir="/tmp/videos")
```

### Network Interception
```python
# Intercept API calls
def handle_route(route):
    # Modify request
    route.continue_(headers={**route.request.headers, "X-Custom": "test"})
    # Or mock response
    route.fulfill(status=200, body='{"mocked": true}')

page.route("**/api/tldr-url", handle_route)
```

### Wait for Network Requests
```python
# Wait for specific API call
with page.expect_response("**/api/scrape") as response_info:
    page.click("#scrapeBtn")

response = response_info.value
print(response.status())  # 200
print(response.json())    # Response body as JSON
```

### Console Logs
```python
# Listen to browser console
page.on("console", lambda msg: print(f"Console: {msg.text()}"))

# Now when you click things, you'll see console.log output!
```

### Keyboard & Mouse
```python
# Type text
page.type("#input", "Hello world")

# Press keys
page.keyboard.press("Enter")
page.keyboard.press("Control+A")

# Hover
page.hover(".article-card")

# Drag and drop
page.drag_and_drop(".source", ".target")
```

### Multiple States/Sessions
```python
# Test with different localStorage states
for state in ["empty", "cached", "partial"]:
    context = browser.new_context()
    page = context.new_page()

    if state == "cached":
        page.evaluate("() => { /* pre-populate cache */ }")

    # Run test
    page.goto("http://localhost:5001/")
    # ... test logic

    context.close()
```

### Accessibility Testing
```python
# Check ARIA labels
aria_label = page.locator("button").get_attribute("aria-label")

# Check keyboard navigation
page.keyboard.press("Tab")
focused = page.evaluate("() => document.activeElement.id")
assert focused == "scrapeBtn"
```

### Visual Regression Testing
```python
# Compare screenshots (with pytest-playwright)
expect(page).to_have_screenshot("homepage.png")
# Fails if pixels changed!
```

---

## Complete Test Example for Your Flow

```python
from playwright.sync_api import sync_playwright

def test_complete_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Clear localStorage
        page.goto("http://localhost:5001/")
        page.evaluate("() => localStorage.clear()")

        # 2. Scrape
        page.fill("#start_date", "2024-11-01")
        page.fill("#end_date", "2024-11-01")
        page.click("#scrapeBtn")
        page.wait_for_selector("button:has-text('Scrape Newsletters')")

        # 3. Verify results
        first_article = page.locator(".article-card").first
        assert first_article.is_visible()

        # 4. Get baseline state
        classes_before = first_article.get_attribute("class")
        bbox_before = first_article.bounding_box()

        # 5. Click TLDR
        first_article.locator(".tldr-btn").click()
        tldr_content = first_article.locator(".inline-tldr")
        tldr_content.wait_for(timeout=30000)
        assert tldr_content.is_visible()

        # 6. Verify TLDR in localStorage
        has_tldr_cache = page.evaluate("""
            () => {
                for (let key of Object.keys(localStorage)) {
                    if (key.includes('tldr')) return true
                }
                return false
            }
        """)
        assert has_tldr_cache

        # 7. Click Remove
        first_article.locator(".remove-article-btn").click()
        page.wait_for_timeout(500)

        # 8. Verify style changed
        classes_after = first_article.get_attribute("class")
        assert "removed" in classes_after
        assert "removed" not in classes_before

        # 9. Verify button text changed
        button_text = first_article.locator(".remove-article-btn").text_content()
        assert button_text == "Restore"

        # 10. Verify position/style changed
        bbox_after = first_article.bounding_box()
        print(f"Position changed: {bbox_before['y']} → {bbox_after['y']}")

        browser.close()
        print("✅ ALL ASSERTIONS PASSED!")

test_complete_flow()
```

---

## Why Playwright is Perfect for This

1. **Full localStorage control** - Read, write, pre-seed, verify
2. **Style/position testing** - `bounding_box()`, `getComputedStyle()`
3. **Smart waiting** - Auto-waits for elements, no flaky tests
4. **State assertions** - Classes, attributes, text content, visibility
5. **JavaScript execution** - Run ANY code in the browser context
6. **Network interception** - Mock APIs, verify requests
7. **Screenshots/videos** - Visual proof of state changes
8. **Console access** - See browser logs
9. **Multiple contexts** - Test different localStorage states

---

## Answer to Your Questions

> "Can playwright do all of those?"

**YES!** Every single thing you mentioned:
- ✅ Scraping & waiting for results
- ✅ Pressing TLDR & waiting for content
- ✅ Asserting content is displayed
- ✅ Pressing Remove & verifying style/position changes
- ✅ Testing localStorage (full read/write access!)

> "I haven't talked about testing headless clientStorage which i hope any of them supports"

**Playwright has COMPLETE localStorage support!** You can:
- Read any key/value
- Write any key/value
- Clear storage
- Pre-seed test data
- Verify state changes persist
- Test cache hits/misses
- All of this works in headless mode!

---

## Bottom Line

Playwright is **specifically designed** for exactly what you want to do. It's the best tool for testing modern web apps with client-side state.

Your TLDRScraper app is the perfect use case for Playwright. 🎯
