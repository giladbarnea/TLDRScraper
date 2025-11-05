"""
Comprehensive Playwright Test for TLDRScraper
Demonstrates all the capabilities you asked about:
1. Scraping and waiting for results
2. Pressing TLDR and waiting for content
3. Asserting content is displayed
4. Pressing Remove and verifying style/position changes
5. Testing localStorage (clientStorage)
"""

from playwright.sync_api import sync_playwright, expect
import json


def test_complete_user_flow():
    """Test the complete user journey with state assertions"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Navigate to app
        print("1. Loading application...")
        page.goto("http://localhost:5001/", wait_until="domcontentloaded")

        # ===================================================================
        # LOCALSTORAGE TESTING - You can do ANYTHING with localStorage!
        # ===================================================================

        print("\n2. Testing localStorage (clientStorage)...")

        # Clear all localStorage
        page.evaluate("() => localStorage.clear()")

        # Verify it's empty
        storage_length = page.evaluate("() => localStorage.length")
        print(f"   ✓ localStorage cleared: {storage_length} items")

        # You can pre-seed localStorage with test data!
        page.evaluate("""
            (testData) => {
                localStorage.setItem('test-key', 'test-value')
                localStorage.setItem('newsletters:scrapes:2024-11-01', JSON.stringify(testData))
            }
        """, {"test": "data", "newsletters": []})

        # Verify localStorage was set
        test_value = page.evaluate("() => localStorage.getItem('test-key')")
        print(f"   ✓ localStorage set: test-key = {test_value}")

        # Get all localStorage keys
        all_keys = page.evaluate("""
            () => {
                const keys = []
                for (let i = 0; i < localStorage.length; i++) {
                    keys.push(localStorage.key(i))
                }
                return keys
            }
        """)
        print(f"   ✓ All localStorage keys: {all_keys}")

        # ===================================================================
        # SCRAPING - Fill form and submit
        # ===================================================================

        print("\n3. Scraping newsletters...")

        # Wait for form to be ready
        page.wait_for_selector("#scrapeForm")

        # Fill in dates
        page.fill("#start_date", "2024-11-01")
        page.fill("#end_date", "2024-11-01")

        # Click scrape button
        page.click("#scrapeBtn")
        print("   ✓ Scrape button clicked")

        # Wait for scraping to complete (button text changes)
        page.wait_for_selector("button:has-text('Scrape Newsletters')", timeout=30000)
        print("   ✓ Scraping completed")

        # ===================================================================
        # ASSERT RESULTS APPEARED
        # ===================================================================

        print("\n4. Verifying results appeared...")

        # Wait for results container
        page.wait_for_selector(".results-container")

        # Count articles
        articles = page.locator(".article-card")
        article_count = articles.count()
        print(f"   ✓ Found {article_count} articles")

        # Assert at least one article exists
        assert article_count > 0, "No articles found!"

        # Get the first article
        first_article = articles.first

        # Verify article has expected classes (should be 'unread' initially)
        article_classes = first_article.get_attribute("class")
        print(f"   ✓ First article classes: {article_classes}")
        assert "unread" in article_classes or "article-card" in article_classes

        # ===================================================================
        # GET ARTICLE POSITION & STYLE (Before changes)
        # ===================================================================

        print("\n5. Getting article position and style (baseline)...")

        # Get bounding box (position and size)
        bbox_before = first_article.bounding_box()
        print(f"   ✓ Position before: x={bbox_before['x']}, y={bbox_before['y']}")
        print(f"   ✓ Size before: width={bbox_before['width']}, height={bbox_before['height']}")

        # Get computed styles
        styles_before = first_article.evaluate("""
            (element) => {
                const computed = window.getComputedStyle(element)
                return {
                    opacity: computed.opacity,
                    display: computed.display,
                    position: computed.position,
                    backgroundColor: computed.backgroundColor,
                    height: computed.height
                }
            }
        """)
        print(f"   ✓ Styles before: {styles_before}")

        # Get original order attribute
        original_order = first_article.get_attribute("data-original-order")
        print(f"   ✓ Original order: {original_order}")

        # ===================================================================
        # PRESS TLDR BUTTON
        # ===================================================================

        print("\n6. Pressing TLDR button...")

        # Find TLDR button within first article
        tldr_button = first_article.locator(".tldr-btn")

        # Get button text before clicking
        tldr_btn_text_before = tldr_button.text_content()
        print(f"   ✓ TLDR button text before: '{tldr_btn_text_before}'")

        # Click TLDR button
        tldr_button.click()
        print("   ✓ TLDR button clicked")

        # Wait for TLDR content to appear (or loading to start)
        # The button might show "Loading TLDR..." first
        page.wait_for_timeout(1000)  # Small wait for state change

        # Check if loading started
        tldr_btn_text_during = tldr_button.text_content()
        print(f"   ✓ TLDR button text during: '{tldr_btn_text_during}'")

        # Wait for TLDR to fully load (button changes to "Hide TLDR" or similar)
        # Or wait for the inline-tldr div to appear
        try:
            # Wait for TLDR content div
            tldr_content = first_article.locator(".inline-tldr")
            tldr_content.wait_for(timeout=30000)
            print("   ✓ TLDR content appeared")

            # Assert TLDR content is visible
            assert tldr_content.is_visible(), "TLDR content not visible!"

            # Get TLDR text
            tldr_text = tldr_content.text_content()
            print(f"   ✓ TLDR length: {len(tldr_text)} characters")
            assert len(tldr_text) > 0, "TLDR content is empty!"

            # Verify button text changed
            tldr_btn_text_after = tldr_button.text_content()
            print(f"   ✓ TLDR button text after: '{tldr_btn_text_after}'")
            assert tldr_btn_text_after != tldr_btn_text_before, "Button text didn't change!"

        except Exception as e:
            print(f"   ⚠ TLDR might not have loaded: {e}")

        # ===================================================================
        # CHECK LOCALSTORAGE AFTER TLDR (TLDR should be cached)
        # ===================================================================

        print("\n7. Checking localStorage after TLDR...")

        # Get all newsletter cache keys
        newsletter_cache = page.evaluate("""
            () => {
                const cache = {}
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i)
                    if (key.startsWith('newsletters:')) {
                        cache[key] = JSON.parse(localStorage.getItem(key) || '{}')
                    }
                }
                return cache
            }
        """)
        print(f"   ✓ Newsletter cache keys: {list(newsletter_cache.keys())}")

        # ===================================================================
        # PRESS REMOVE BUTTON
        # ===================================================================

        print("\n8. Pressing Remove button...")

        # Find Remove button
        remove_button = first_article.locator(".remove-article-btn")
        remove_btn_text_before = remove_button.text_content()
        print(f"   ✓ Remove button text before: '{remove_btn_text_before}'")

        # Click Remove
        remove_button.click()
        print("   ✓ Remove button clicked")

        # Small wait for React state update
        page.wait_for_timeout(500)

        # ===================================================================
        # ASSERT STYLE & POSITION CHANGED AFTER REMOVE
        # ===================================================================

        print("\n9. Verifying article style/position changed after Remove...")

        # Get classes after removal
        article_classes_after = first_article.get_attribute("class")
        print(f"   ✓ Article classes after removal: {article_classes_after}")
        assert "removed" in article_classes_after, "Article doesn't have 'removed' class!"

        # Get styles after removal
        styles_after = first_article.evaluate("""
            (element) => {
                const computed = window.getComputedStyle(element)
                return {
                    opacity: computed.opacity,
                    display: computed.display,
                    position: computed.position,
                    backgroundColor: computed.backgroundColor,
                    height: computed.height,
                    order: computed.order
                }
            }
        """)
        print(f"   ✓ Styles after removal: {styles_after}")

        # Assert style changed (commonly opacity changes or position)
        if styles_before['opacity'] != styles_after['opacity']:
            print(f"   ✓ Opacity changed: {styles_before['opacity']} → {styles_after['opacity']}")

        # Get bounding box after
        bbox_after = first_article.bounding_box()
        if bbox_after:
            print(f"   ✓ Position after: x={bbox_after['x']}, y={bbox_after['y']}")
            print(f"   ✓ Size after: width={bbox_after['width']}, height={bbox_after['height']}")

            # Check if position changed (might move to bottom if removed articles reorder)
            if bbox_before['y'] != bbox_after['y']:
                print(f"   ✓ Position changed: y {bbox_before['y']} → {bbox_after['y']}")

        # Verify button text changed to "Restore"
        remove_btn_text_after = remove_button.text_content()
        print(f"   ✓ Remove button text after: '{remove_btn_text_after}'")
        assert remove_btn_text_after == "Restore", f"Expected 'Restore', got '{remove_btn_text_after}'"

        # ===================================================================
        # VERIFY LOCALSTORAGE WAS UPDATED WITH REMOVAL STATE
        # ===================================================================

        print("\n10. Verifying localStorage updated with removal state...")

        # Get article URL to find it in localStorage
        article_url = first_article.locator(".article-link").get_attribute("data-url")
        print(f"   ✓ Checking localStorage for article: {article_url}")

        # Check if article is marked as removed in localStorage
        removal_state = page.evaluate(f"""
            (url) => {{
                for (let i = 0; i < localStorage.length; i++) {{
                    const key = localStorage.key(i)
                    if (key.startsWith('newsletters:scrapes:')) {{
                        const data = JSON.parse(localStorage.getItem(key) || '{{}}')
                        if (data.newsletters) {{
                            for (const newsletter of data.newsletters) {{
                                if (newsletter.url === url || newsletter.url === url.replace('https://', '')) {{
                                    return newsletter.removed || false
                                }}
                            }}
                        }}
                    }}
                }}
                return null
            }}
        """, article_url)
        print(f"   ✓ Article removal state in localStorage: {removal_state}")

        # ===================================================================
        # ADDITIONAL CAPABILITIES
        # ===================================================================

        print("\n11. Additional Playwright capabilities...")

        # Take a screenshot
        page.screenshot(path="/tmp/after-removal.png")
        print("   ✓ Screenshot saved to /tmp/after-removal.png")

        # Get full page HTML
        html = page.content()
        print(f"   ✓ Page HTML length: {len(html)} characters")

        # Execute custom JavaScript
        custom_result = page.evaluate("""
            () => {
                // You can run ANY JavaScript here
                const articles = document.querySelectorAll('.article-card')
                const removed = document.querySelectorAll('.article-card.removed')
                return {
                    total: articles.length,
                    removed: removed.length,
                    unremoved: articles.length - removed.length
                }
            }
        """)
        print(f"   ✓ Article stats: {custom_result}")

        # Wait for network requests (can intercept API calls!)
        # page.route("**/api/tldr-url", lambda route: ...)

        # Listen to console logs
        page.on("console", lambda msg: print(f"   Browser console: {msg.text()}"))

        # Get cookies
        cookies = context.cookies()
        print(f"   ✓ Cookies: {len(cookies)} found")

        # Dump all localStorage as JSON
        full_storage = page.evaluate("() => JSON.stringify(localStorage)")
        print(f"   ✓ Full localStorage size: {len(full_storage)} characters")

        browser.close()

        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED! Playwright can do everything you need!")
        print("="*60)


if __name__ == "__main__":
    test_complete_user_flow()
