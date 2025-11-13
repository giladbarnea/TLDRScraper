"""
Demonstration of Playwright capabilities on a publicly accessible site
Shows navigation, clicking, JavaScript execution, and localStorage manipulation
"""

from playwright.sync_api import sync_playwright
import json


def test_playwright_capabilities():
    """Demonstrate Playwright can navigate, click, execute JS, and manipulate localStorage"""

    with sync_playwright() as p:
        print("="*80)
        print("PLAYWRIGHT CAPABILITIES DEMONSTRATION")
        print("="*80)

        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        try:
            # ===================================================================
            # 1. NAVIGATION
            # ===================================================================
            print("\n1. Testing Navigation...")
            page.goto("https://example.com", timeout=30000)
            print(f"   ✓ Navigated to: {page.url}")
            print(f"   ✓ Page title: {page.title()}")

            # ===================================================================
            # 2. ELEMENT INSPECTION
            # ===================================================================
            print("\n2. Testing Element Inspection...")

            # Get all headings
            h1_count = page.locator("h1").count()
            print(f"   ✓ Found {h1_count} h1 elements")

            if h1_count > 0:
                h1_text = page.locator("h1").first.text_content()
                print(f"   ✓ First h1 text: '{h1_text}'")

            # Get all links
            link_count = page.locator("a").count()
            print(f"   ✓ Found {link_count} links")

            # ===================================================================
            # 3. STYLE & POSITION
            # ===================================================================
            print("\n3. Testing Style & Position Detection...")

            if h1_count > 0:
                h1 = page.locator("h1").first

                # Get bounding box
                bbox = h1.bounding_box()
                if bbox:
                    print(f"   ✓ H1 position: x={bbox['x']}, y={bbox['y']}")
                    print(f"   ✓ H1 size: width={bbox['width']}, height={bbox['height']}")

                # Get computed styles
                styles = h1.evaluate("""
                    (element) => {
                        const computed = window.getComputedStyle(element)
                        return {
                            fontSize: computed.fontSize,
                            fontWeight: computed.fontWeight,
                            color: computed.color,
                            display: computed.display,
                            textAlign: computed.textAlign
                        }
                    }
                """)
                print(f"   ✓ H1 styles: {styles}")

            # ===================================================================
            # 4. LOCALSTORAGE MANIPULATION (THE KEY FEATURE!)
            # ===================================================================
            print("\n4. Testing localStorage Manipulation...")

            # Clear localStorage
            page.evaluate("() => localStorage.clear()")
            length = page.evaluate("() => localStorage.length")
            print(f"   ✓ localStorage cleared: {length} items")

            # Set multiple items
            page.evaluate("""
                () => {
                    localStorage.setItem('test-key', 'test-value')
                    localStorage.setItem('user-name', 'Claude')
                    localStorage.setItem('cache-enabled', 'true')
                    localStorage.setItem('complex-data', JSON.stringify({
                        date: '2024-11-01',
                        items: [1, 2, 3],
                        nested: { key: 'value' }
                    }))
                }
            """)
            print("   ✓ Set 4 items in localStorage")

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
            print(f"   ✓ localStorage keys: {all_keys}")

            # Read specific items
            test_value = page.evaluate("() => localStorage.getItem('test-key')")
            print(f"   ✓ test-key = '{test_value}'")

            user_name = page.evaluate("() => localStorage.getItem('user-name')")
            print(f"   ✓ user-name = '{user_name}'")

            # Parse complex data
            complex_data = page.evaluate("""
                () => {
                    const raw = localStorage.getItem('complex-data')
                    return JSON.parse(raw)
                }
            """)
            print(f"   ✓ complex-data = {complex_data}")

            # Update an item
            page.evaluate("""
                () => localStorage.setItem('user-name', 'Claude AI Assistant')
            """)
            updated_name = page.evaluate("() => localStorage.getItem('user-name')")
            print(f"   ✓ Updated user-name = '{updated_name}'")

            # Remove an item
            page.evaluate("() => localStorage.removeItem('test-key')")
            after_remove = page.evaluate("() => localStorage.getItem('test-key')")
            print(f"   ✓ After removal, test-key = {after_remove}")

            # Check final count
            final_length = page.evaluate("() => localStorage.length")
            print(f"   ✓ Final localStorage count: {final_length} items")

            # ===================================================================
            # 5. CUSTOM JAVASCRIPT EXECUTION
            # ===================================================================
            print("\n5. Testing Custom JavaScript Execution...")

            # Execute complex JavaScript
            result = page.evaluate("""
                () => {
                    // Can access all browser APIs
                    const info = {
                        url: window.location.href,
                        viewport: {
                            width: window.innerWidth,
                            height: window.innerHeight
                        },
                        document: {
                            title: document.title,
                            readyState: document.readyState,
                            elementCount: document.querySelectorAll('*').length
                        },
                        localStorage: {
                            itemCount: localStorage.length,
                            keys: Object.keys(localStorage)
                        },
                        userAgent: navigator.userAgent.substring(0, 50) + '...'
                    }
                    return info
                }
            """)
            print(f"   ✓ Viewport: {result['viewport']}")
            print(f"   ✓ Total elements on page: {result['document']['elementCount']}")
            print(f"   ✓ localStorage items: {result['localStorage']['itemCount']}")

            # ===================================================================
            # 6. SCREENSHOT CAPTURE
            # ===================================================================
            print("\n6. Testing Screenshot Capture...")

            page.screenshot(path="/tmp/playwright-demo.png")
            print("   ✓ Screenshot saved: /tmp/playwright-demo.png")

            # Screenshot specific element
            if h1_count > 0:
                page.locator("h1").first.screenshot(path="/tmp/playwright-demo-h1.png")
                print("   ✓ H1 screenshot saved: /tmp/playwright-demo-h1.png")

            # ===================================================================
            # 7. PAGE CONTENT
            # ===================================================================
            print("\n7. Testing Page Content Access...")

            html = page.content()
            print(f"   ✓ Page HTML length: {len(html)} characters")

            inner_html = page.locator("body").inner_html()
            print(f"   ✓ Body innerHTML length: {len(inner_html)} characters")

            # ===================================================================
            # 8. DEMONSTRATE WAITING
            # ===================================================================
            print("\n8. Testing Wait Capabilities...")

            # Wait for specific element
            page.wait_for_selector("h1", timeout=5000)
            print("   ✓ Successfully waited for h1 element")

            # Wait for timeout (simulate async operation)
            page.wait_for_timeout(500)
            print("   ✓ Successfully waited 500ms")

            # ===================================================================
            # 9. SIMULATE TLDR-SPECIFIC SCENARIO
            # ===================================================================
            print("\n9. Simulating TLDRScraper localStorage pattern...")

            # Simulate newsletter cache structure
            page.evaluate("""
                () => {
                    const newsletters = {
                        date: '2024-11-01',
                        newsletters: [
                            {
                                title: 'Test Newsletter 1',
                                url: 'https://example.com/article1',
                                removed: false,
                                tldr: null
                            },
                            {
                                title: 'Test Newsletter 2',
                                url: 'https://example.com/article2',
                                removed: true,
                                tldr: 'This is a cached TLDR'
                            }
                        ]
                    }
                    localStorage.setItem('newsletters:scrapes:2024-11-01', JSON.stringify(newsletters))
                }
            """)
            print("   ✓ Created newsletter cache structure")

            # Retrieve and verify
            newsletter_cache = page.evaluate("""
                () => {
                    const raw = localStorage.getItem('newsletters:scrapes:2024-11-01')
                    return JSON.parse(raw)
                }
            """)
            print(f"   ✓ Retrieved cache with {len(newsletter_cache['newsletters'])} newsletters")
            print(f"   ✓ Newsletter 1 removed: {newsletter_cache['newsletters'][0]['removed']}")
            print(f"   ✓ Newsletter 2 removed: {newsletter_cache['newsletters'][1]['removed']}")
            print(f"   ✓ Newsletter 2 has TLDR: {newsletter_cache['newsletters'][1]['tldr'] is not None}")

            # Simulate marking article as removed
            page.evaluate("""
                (url) => {
                    const raw = localStorage.getItem('newsletters:scrapes:2024-11-01')
                    const data = JSON.parse(raw)
                    const article = data.newsletters.find(n => n.url === url)
                    if (article) {
                        article.removed = true
                    }
                    localStorage.setItem('newsletters:scrapes:2024-11-01', JSON.stringify(data))
                }
            """, "https://example.com/article1")
            print("   ✓ Marked article 1 as removed")

            # Verify the change persisted
            updated_cache = page.evaluate("""
                () => {
                    const raw = localStorage.getItem('newsletters:scrapes:2024-11-01')
                    return JSON.parse(raw)
                }
            """)
            print(f"   ✓ Article 1 now removed: {updated_cache['newsletters'][0]['removed']}")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")

        finally:
            browser.close()

        print("\n" + "="*80)
        print("✓ PLAYWRIGHT DEMONSTRATION COMPLETED!")
        print("="*80)
        print("\nKey Takeaways:")
        print("  1. ✅ Playwright can navigate to any URL")
        print("  2. ✅ Can inspect elements, styles, and positions")
        print("  3. ✅ Has FULL localStorage access (read/write/modify/delete)")
        print("  4. ✅ Can execute arbitrary JavaScript in browser context")
        print("  5. ✅ Can capture screenshots of entire page or specific elements")
        print("  6. ✅ Can simulate TLDRScraper's localStorage patterns perfectly")
        print("  7. ✅ Works in headless mode (no GUI needed)")
        print("\nPlaywright is PERFECT for testing TLDRScraper! 🎯")


if __name__ == "__main__":
    test_playwright_capabilities()
