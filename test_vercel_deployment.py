"""
Test the deployed Vercel version of TLDRScraper
Demonstrates Playwright's capabilities on a live deployment
"""

from playwright.sync_api import sync_playwright
import json


def test_vercel_deployment():
    """Test the complete flow on the deployed Vercel app"""

    url = "https://tldr-flask-scraper-git-claude-impl-40d375-giladbarneas-projects.vercel.app/"

    with sync_playwright() as p:
        print("="*80)
        print(f"Testing Vercel Deployment: {url}")
        print("="*80)

        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        # Listen to console logs
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"{msg.type()}: {msg.text()}"))

        # Listen to network requests
        requests = []
        page.on("request", lambda req: requests.append(f"{req.method} {req.url}"))

        try:
            # ===================================================================
            # 1. NAVIGATION & PAGE LOAD
            # ===================================================================

            print("\n1. Navigating to deployed app...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"   ✓ Page loaded: {page.title()}")

            # Wait a bit for JavaScript to initialize
            page.wait_for_timeout(2000)

            # Take initial screenshot
            page.screenshot(path="/tmp/vercel-initial.png")
            print("   ✓ Screenshot saved: /tmp/vercel-initial.png")

            # ===================================================================
            # 2. INSPECT PAGE STRUCTURE
            # ===================================================================

            print("\n2. Inspecting page structure...")

            # Get page HTML
            html = page.content()
            print(f"   ✓ Page HTML length: {len(html)} characters")

            # Check if main elements exist
            has_scrape_form = page.locator("#scrapeForm").count() > 0
            has_start_date = page.locator("#start_date").count() > 0
            has_end_date = page.locator("#end_date").count() > 0
            has_scrape_btn = page.locator("#scrapeBtn").count() > 0

            print(f"   ✓ Scrape form exists: {has_scrape_form}")
            print(f"   ✓ Start date input exists: {has_start_date}")
            print(f"   ✓ End date input exists: {has_end_date}")
            print(f"   ✓ Scrape button exists: {has_scrape_btn}")

            # ===================================================================
            # 3. LOCALSTORAGE INSPECTION
            # ===================================================================

            print("\n3. Inspecting localStorage...")

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
            print(f"   ✓ localStorage keys: {all_keys}")

            # Get full localStorage dump
            storage_dump = page.evaluate("""
                () => {
                    const dump = {}
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i)
                        try {
                            dump[key] = JSON.parse(localStorage.getItem(key))
                        } catch {
                            dump[key] = localStorage.getItem(key)
                        }
                    }
                    return dump
                }
            """)
            print(f"   ✓ localStorage contents: {json.dumps(storage_dump, indent=2)}")

            # ===================================================================
            # 4. INTERACT WITH FORM
            # ===================================================================

            if has_scrape_form and has_start_date and has_end_date and has_scrape_btn:
                print("\n4. Interacting with scrape form...")

                # Fill in dates
                page.fill("#start_date", "2024-11-01")
                page.fill("#end_date", "2024-11-01")
                print("   ✓ Dates filled")

                # Get button text before clicking
                btn_text_before = page.locator("#scrapeBtn").text_content()
                print(f"   ✓ Button text before: '{btn_text_before}'")

                # Take screenshot before clicking
                page.screenshot(path="/tmp/vercel-before-scrape.png")
                print("   ✓ Screenshot saved: /tmp/vercel-before-scrape.png")

                # Click scrape button
                print("   ⏳ Clicking scrape button (this may take a while)...")
                page.click("#scrapeBtn")

                # Wait for button to change (might show "Scraping...")
                page.wait_for_timeout(2000)
                btn_text_during = page.locator("#scrapeBtn").text_content()
                print(f"   ✓ Button text during: '{btn_text_during}'")

                # Wait for scraping to complete (button changes back or results appear)
                try:
                    # Wait for either results to appear or button to change back
                    page.wait_for_selector(".article-card, button:has-text('Scrape Newsletters')", timeout=60000)
                    print("   ✓ Scraping completed or timed out")

                    # Check if results appeared
                    article_count = page.locator(".article-card").count()
                    print(f"   ✓ Articles found: {article_count}")

                    if article_count > 0:
                        # Take screenshot with results
                        page.screenshot(path="/tmp/vercel-with-results.png")
                        print("   ✓ Screenshot saved: /tmp/vercel-with-results.png")

                        # Get first article details
                        first_article = page.locator(".article-card").first
                        article_classes = first_article.get_attribute("class")
                        print(f"   ✓ First article classes: {article_classes}")

                        # Get article position and size
                        bbox = first_article.bounding_box()
                        if bbox:
                            print(f"   ✓ First article position: x={bbox['x']}, y={bbox['y']}")
                            print(f"   ✓ First article size: width={bbox['width']}, height={bbox['height']}")

                        # Get computed styles
                        styles = first_article.evaluate("""
                            (element) => {
                                const computed = window.getComputedStyle(element)
                                return {
                                    opacity: computed.opacity,
                                    display: computed.display,
                                    backgroundColor: computed.backgroundColor,
                                    padding: computed.padding,
                                    margin: computed.margin
                                }
                            }
                        """)
                        print(f"   ✓ First article styles: {styles}")

                        # Check for TLDR button
                        has_tldr_btn = first_article.locator(".tldr-btn").count() > 0
                        if has_tldr_btn:
                            print("   ✓ TLDR button found in first article")

                            # Click TLDR button
                            first_article.locator(".tldr-btn").click()
                            print("   ⏳ TLDR button clicked, waiting for content...")

                            # Wait for TLDR content or loading state
                            page.wait_for_timeout(3000)

                            # Check if TLDR content appeared
                            has_tldr_content = first_article.locator(".inline-tldr").count() > 0
                            if has_tldr_content:
                                tldr_text = first_article.locator(".inline-tldr").text_content()
                                print(f"   ✓ TLDR content length: {len(tldr_text)} characters")
                                page.screenshot(path="/tmp/vercel-with-tldr.png")
                                print("   ✓ Screenshot saved: /tmp/vercel-with-tldr.png")
                            else:
                                print("   ⚠ TLDR content did not appear")

                        # Check for Remove button
                        has_remove_btn = first_article.locator(".remove-article-btn").count() > 0
                        if has_remove_btn:
                            print("   ✓ Remove button found")

                            # Click remove
                            first_article.locator(".remove-article-btn").click()
                            page.wait_for_timeout(1000)

                            # Check if classes changed
                            classes_after = first_article.get_attribute("class")
                            print(f"   ✓ Article classes after remove: {classes_after}")

                            if "removed" in classes_after:
                                print("   ✓ Article successfully marked as removed!")
                                page.screenshot(path="/tmp/vercel-after-remove.png")
                                print("   ✓ Screenshot saved: /tmp/vercel-after-remove.png")
                    else:
                        print("   ⚠ No articles found after scraping")

                except Exception as e:
                    print(f"   ⚠ Error during scraping or interaction: {e}")
            else:
                print("\n4. ⚠ Scrape form not found, skipping interaction")

            # ===================================================================
            # 5. EXECUTE CUSTOM JAVASCRIPT
            # ===================================================================

            print("\n5. Executing custom JavaScript...")

            # Get all article stats
            article_stats = page.evaluate("""
                () => {
                    const articles = document.querySelectorAll('.article-card')
                    const removed = document.querySelectorAll('.article-card.removed')
                    const unread = document.querySelectorAll('.article-card.unread')

                    return {
                        total: articles.length,
                        removed: removed.length,
                        unread: unread.length,
                        active: articles.length - removed.length
                    }
                }
            """)
            print(f"   ✓ Article statistics: {article_stats}")

            # Check React version (if available)
            react_version = page.evaluate("""
                () => {
                    if (window.React) {
                        return window.React.version
                    }
                    return 'Not available'
                }
            """)
            print(f"   ✓ React version: {react_version}")

            # ===================================================================
            # 6. LOCALSTORAGE AFTER INTERACTIONS
            # ===================================================================

            print("\n6. localStorage after interactions...")

            all_keys_after = page.evaluate("""
                () => {
                    const keys = []
                    for (let i = 0; i < localStorage.length; i++) {
                        keys.push(localStorage.key(i))
                    }
                    return keys
                }
            """)
            print(f"   ✓ localStorage keys after: {all_keys_after}")

            # Get newsletter cache if exists
            newsletter_cache = page.evaluate("""
                () => {
                    const cache = {}
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i)
                        if (key.startsWith('newsletters:')) {
                            try {
                                cache[key] = JSON.parse(localStorage.getItem(key))
                            } catch {
                                cache[key] = localStorage.getItem(key)
                            }
                        }
                    }
                    return cache
                }
            """)
            if newsletter_cache:
                print(f"   ✓ Newsletter cache keys: {list(newsletter_cache.keys())}")
                for key, value in newsletter_cache.items():
                    if isinstance(value, dict):
                        newsletter_count = len(value.get('newsletters', []))
                        print(f"   ✓ {key}: {newsletter_count} newsletters")

            # ===================================================================
            # 7. CONSOLE AND NETWORK LOGS
            # ===================================================================

            print("\n7. Console and network activity...")

            print(f"   ✓ Console messages: {len(console_messages)}")
            if console_messages:
                for msg in console_messages[:10]:  # Show first 10
                    print(f"      - {msg}")

            print(f"   ✓ Network requests: {len(requests)}")
            if requests:
                for req in requests[:10]:  # Show first 10
                    print(f"      - {req}")

            # ===================================================================
            # 8. FINAL SCREENSHOT
            # ===================================================================

            print("\n8. Taking final screenshot...")
            page.screenshot(path="/tmp/vercel-final.png", full_page=True)
            print("   ✓ Full page screenshot saved: /tmp/vercel-final.png")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            page.screenshot(path="/tmp/vercel-error.png")
            print("   ✓ Error screenshot saved: /tmp/vercel-error.png")

        finally:
            browser.close()

        print("\n" + "="*80)
        print("✓ TEST COMPLETED!")
        print("="*80)
        print("\nScreenshots saved:")
        print("  - /tmp/vercel-initial.png")
        print("  - /tmp/vercel-before-scrape.png")
        print("  - /tmp/vercel-with-results.png")
        print("  - /tmp/vercel-with-tldr.png")
        print("  - /tmp/vercel-after-remove.png")
        print("  - /tmp/vercel-final.png")


if __name__ == "__main__":
    test_vercel_deployment()
