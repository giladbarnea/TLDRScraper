"""
Simple debugging test to verify Playwright can interact with the app
"""

from playwright.sync_api import sync_playwright

def test_basic_page_load():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("1. Navigating to app...")
        try:
            page.goto("http://localhost:5001/", wait_until="domcontentloaded", timeout=10000)
            print("   ✓ Page loaded")
        except Exception as e:
            print(f"   ✗ Failed to load page: {e}")
            browser.close()
            return

        print("\n2. Getting page title...")
        try:
            title = page.title()
            print(f"   ✓ Page title: {title}")
        except Exception as e:
            print(f"   ✗ Failed to get title: {e}")

        print("\n3. Taking screenshot...")
        try:
            page.screenshot(path="/tmp/debug-page-load.png")
            print("   ✓ Screenshot saved to /tmp/debug-page-load.png")
        except Exception as e:
            print(f"   ✗ Failed to take screenshot: {e}")

        print("\n4. Getting page content (first 500 chars)...")
        try:
            content = page.content()
            print(f"   ✓ Content: {content[:500]}...")
        except Exception as e:
            print(f"   ✗ Failed to get content: {e}")

        print("\n5. Waiting for form...")
        try:
            page.wait_for_selector("#scrapeForm", timeout=20000)
            print("   ✓ Form found")
        except Exception as e:
            print(f"   ✗ Form not found: {e}")

        print("\n6. Trying to interact with localStorage...")
        try:
            page.evaluate("() => localStorage.clear()")
            print("   ✓ localStorage.clear() executed")

            length = page.evaluate("() => localStorage.length")
            print(f"   ✓ localStorage.length = {length}")
        except Exception as e:
            print(f"   ✗ localStorage interaction failed: {e}")

        browser.close()
        print("\n✓ Basic debugging test complete")

if __name__ == "__main__":
    test_basic_page_load()
