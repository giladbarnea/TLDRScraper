"""
Live Playwright test for TLDRScraper Vercel deployment
Tests the actual deployed application with real interactions
"""

from playwright.sync_api import sync_playwright
import json


def test_vercel_live():
    """Test the live Vercel deployment"""

    url = "https://tldr-flask-scraper-git-claude-impl-40d375-giladbarneas-projects.vercel.app/"

    with sync_playwright() as p:
        print("="*80)
        print("TESTING LIVE VERCEL DEPLOYMENT")
        print(f"URL: {url}")
        print("="*80)

        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        # Track console and errors
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type()}] {msg.text()}"))

        page.on("pageerror", lambda exc: print(f"   ❌ Page error: {exc}"))

        try:
            # ===================================================================
            # 1. NAVIGATE AND LOAD PAGE
            # ===================================================================
            print("\n1. Loading page...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"   ✓ Page loaded: {page.title()}")
            print(f"   ✓ URL: {page.url}")

            # Wait for React to initialize
            page.wait_for_timeout(2000)

            # ===================================================================
            # 2. INSPECT PAGE STRUCTURE
            # ===================================================================
            print("\n2. Inspecting page structure...")

            # Check for main elements
            has_form = page.locator("#scrapeForm").count() > 0
            has_start_date = page.locator("#start_date").count() > 0
            has_end_date = page.locator("#end_date").count() > 0
            has_scrape_btn = page.locator("#scrapeBtn").count() > 0

            print(f"   ✓ Scrape form: {has_form}")
            print(f"   ✓ Start date input: {has_start_date}")
            print(f"   ✓ End date input: {has_end_date}")
            print(f"   ✓ Scrape button: {has_scrape_btn}")

            if not (has_form and has_start_date and has_end_date and has_scrape_btn):
                print("   ⚠ Missing expected elements!")
                page.screenshot(path="/tmp/vercel_missing_elements.png")
                print("   ✓ Screenshot saved: /tmp/vercel_missing_elements.png")
                return

            # ===================================================================
            # 3. TEST LOCALSTORAGE ACCESS
            # ===================================================================
            print("\n3. Testing localStorage access...")

            # Clear localStorage
            page.evaluate("() => localStorage.clear()")
            length = page.evaluate("() => localStorage.length")
            print(f"   ✓ localStorage cleared: {length} items")

            # Set test value
            page.evaluate("() => localStorage.setItem('test', 'playwright-works')")
            test_value = page.evaluate("() => localStorage.getItem('test')")
            print(f"   ✓ localStorage read/write works: {test_value}")

            # ===================================================================
            # 4. INTERACT WITH FORM
            # ===================================================================
            print("\n4. Testing form interaction...")

            # Fill dates
            page.fill("#start_date", "2024-11-01")
            page.fill("#end_date", "2024-11-01")
            print("   ✓ Dates filled: 2024-11-01")

            # Get button text before clicking
            btn_text_before = page.locator("#scrapeBtn").text_content()
            print(f"   ✓ Button text before: '{btn_text_before}'")

            # Take screenshot before scraping
            page.screenshot(path="/tmp/vercel_before_scrape.png")
            print("   ✓ Screenshot: /tmp/vercel_before_scrape.png")

            # ===================================================================
            # 5. CLICK SCRAPE BUTTON
            # ===================================================================
            print("\n5. Clicking scrape button...")
            print("   ⏳ This may take 30-60 seconds...")

            page.click("#scrapeBtn")

            # Wait for button to change (shows "Scraping...")
            page.wait_for_timeout(2000)
            btn_text_during = page.locator("#scrapeBtn").text_content()
            print(f"   ✓ Button text during: '{btn_text_during}'")

            # Wait for scraping to complete (button changes back or results appear)
            try:
                # Wait up to 90 seconds for results or button to change back
                page.wait_for_selector(
                    ".article-card, button:has-text('Scrape Newsletters')",
                    timeout=90000
                )
                print("   ✓ Scraping completed")

            except Exception as e:
                print(f"   ⚠ Scraping timed out or failed: {e}")
                page.screenshot(path="/tmp/vercel_scrape_timeout.png")
                print("   ✓ Screenshot: /tmp/vercel_scrape_timeout.png")
                return

            # ===================================================================
            # 6. VERIFY RESULTS
            # ===================================================================
            print("\n6. Verifying results...")

            article_count = page.locator(".article-card").count()
            print(f"   ✓ Articles found: {article_count}")

            if article_count == 0:
                print("   ⚠ No articles found")
                page.screenshot(path="/tmp/vercel_no_articles.png")
                print("   ✓ Screenshot: /tmp/vercel_no_articles.png")

                # Check localStorage anyway
                storage_keys = page.evaluate("""
                    () => {
                        const keys = []
                        for (let i = 0; i < localStorage.length; i++) {
                            keys.push(localStorage.key(i))
                        }
                        return keys
                    }
                """)
                print(f"   ✓ localStorage keys: {storage_keys}")
                return

            # Take screenshot with results
            page.screenshot(path="/tmp/vercel_with_results.png")
            print("   ✓ Screenshot: /tmp/vercel_with_results.png")

            # ===================================================================
            # 7. INSPECT FIRST ARTICLE
            # ===================================================================
            print("\n7. Inspecting first article...")

            first_article = page.locator(".article-card").first

            # Get classes
            article_classes = first_article.get_attribute("class")
            print(f"   ✓ Article classes: {article_classes}")

            # Get position and styles
            bbox = first_article.bounding_box()
            if bbox:
                print(f"   ✓ Position: x={bbox['x']:.0f}, y={bbox['y']:.0f}")
                print(f"   ✓ Size: {bbox['width']:.0f} x {bbox['height']:.0f}")

            styles = first_article.evaluate("""
                (el) => {
                    const computed = window.getComputedStyle(el)
                    return {
                        opacity: computed.opacity,
                        display: computed.display,
                        padding: computed.padding
                    }
                }
            """)
            print(f"   ✓ Styles: {styles}")

            # ===================================================================
            # 8. VERIFY LOCALSTORAGE WAS UPDATED
            # ===================================================================
            print("\n8. Verifying localStorage...")

            storage_keys = page.evaluate("""
                () => {
                    const keys = []
                    for (let i = 0; i < localStorage.length; i++) {
                        keys.push(localStorage.key(i))
                    }
                    return keys
                }
            """)
            print(f"   ✓ localStorage keys: {storage_keys}")

            # Get newsletter cache
            newsletter_cache = page.evaluate("""
                () => {
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i)
                        if (key.startsWith('newsletters:scrapes:')) {
                            return {
                                key: key,
                                data: JSON.parse(localStorage.getItem(key))
                            }
                        }
                    }
                    return null
                }
            """)

            if newsletter_cache:
                print(f"   ✓ Cache key: {newsletter_cache['key']}")
                print(f"   ✓ Newsletters cached: {len(newsletter_cache['data'].get('newsletters', []))}")
            else:
                print("   ⚠ No newsletter cache found in localStorage")

            # ===================================================================
            # 9. TEST TLDR BUTTON (IF AVAILABLE)
            # ===================================================================
            print("\n9. Testing TLDR button...")

            has_tldr_btn = first_article.locator(".tldr-btn").count() > 0
            if has_tldr_btn:
                print("   ✓ TLDR button found")

                tldr_btn = first_article.locator(".tldr-btn")
                tldr_btn_text_before = tldr_btn.text_content()
                print(f"   ✓ Button text: '{tldr_btn_text_before}'")

                # Click TLDR
                tldr_btn.click()
                print("   ⏳ Clicked TLDR, waiting for response...")

                # Wait for TLDR to load (may take time)
                page.wait_for_timeout(5000)

                # Check if TLDR appeared
                has_tldr_content = first_article.locator(".inline-tldr").count() > 0
                if has_tldr_content:
                    tldr_text = first_article.locator(".inline-tldr").text_content()
                    print(f"   ✓ TLDR appeared: {len(tldr_text)} chars")
                    page.screenshot(path="/tmp/vercel_with_tldr.png")
                    print("   ✓ Screenshot: /tmp/vercel_with_tldr.png")
                else:
                    print("   ⚠ TLDR did not appear yet")
            else:
                print("   ⚠ TLDR button not found")

            # ===================================================================
            # 10. TEST REMOVE BUTTON (IF AVAILABLE)
            # ===================================================================
            print("\n10. Testing Remove button...")

            has_remove_btn = first_article.locator(".remove-article-btn").count() > 0
            if has_remove_btn:
                print("   ✓ Remove button found")

                classes_before = first_article.get_attribute("class")

                # Click remove
                first_article.locator(".remove-article-btn").click()
                page.wait_for_timeout(500)

                classes_after = first_article.get_attribute("class")
                print(f"   ✓ Classes before: {classes_before}")
                print(f"   ✓ Classes after: {classes_after}")

                if "removed" in classes_after and "removed" not in classes_before:
                    print("   ✓ Article successfully marked as removed!")
                    page.screenshot(path="/tmp/vercel_after_remove.png")
                    print("   ✓ Screenshot: /tmp/vercel_after_remove.png")
                else:
                    print("   ⚠ Remove state may not have changed")
            else:
                print("   ⚠ Remove button not found")

            # ===================================================================
            # 11. EXECUTE CUSTOM JAVASCRIPT
            # ===================================================================
            print("\n11. Executing custom JavaScript...")

            stats = page.evaluate("""
                () => {
                    const articles = document.querySelectorAll('.article-card')
                    const removed = document.querySelectorAll('.article-card.removed')
                    return {
                        total: articles.length,
                        removed: removed.length,
                        active: articles.length - removed.length
                    }
                }
            """)
            print(f"   ✓ Article statistics: {stats}")

            # ===================================================================
            # 12. FINAL SCREENSHOT
            # ===================================================================
            print("\n12. Saving final screenshot...")
            page.screenshot(path="/tmp/vercel_final.png", full_page=True)
            print("   ✓ Full page screenshot: /tmp/vercel_final.png")

            # ===================================================================
            # 13. CONSOLE LOGS
            # ===================================================================
            print("\n13. Browser console logs...")
            if console_logs:
                print(f"   ✓ Captured {len(console_logs)} console messages")
                for msg in console_logs[:10]:  # Show first 10
                    print(f"      {msg}")
            else:
                print("   ✓ No console messages")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            page.screenshot(path="/tmp/vercel_error.png")
            print("   ✓ Error screenshot: /tmp/vercel_error.png")
            import traceback
            traceback.print_exc()

        finally:
            browser.close()

        print("\n" + "="*80)
        print("✓ TEST COMPLETED")
        print("="*80)
        print("\nScreenshots saved in /tmp/:")
        print("  - vercel_before_scrape.png")
        print("  - vercel_with_results.png")
        print("  - vercel_with_tldr.png")
        print("  - vercel_after_remove.png")
        print("  - vercel_final.png")


if __name__ == "__main__":
    test_vercel_live()
