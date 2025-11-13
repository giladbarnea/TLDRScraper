"""
Phase 5 local smoke test - tries everything to make Playwright work
"""

from playwright.sync_api import sync_playwright
import os


def test_local_phase5_aggressive():
    """Try all possible options to test localhost"""

    url = "http://localhost:3000/"

    with sync_playwright() as p:
        print("="*80)
        print("PHASE 5 LOCAL SMOKE TEST")
        print(f"URL: {url}")
        print("="*80)

        # Try EVERY possible browser launch option
        launch_options = {
            'headless': True,
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-blink-features=AutomationControlled',
            ]
        }

        print("\n📋 Launch options:")
        for key, val in launch_options.items():
            if key == 'args':
                print(f"   {key}:")
                for arg in val:
                    print(f"      {arg}")
            else:
                print(f"   {key}: {val}")

        browser = p.chromium.launch(**launch_options)

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            bypass_csp=True,
            locale='en-US',
            timezone_id='America/New_York',
        )

        page = context.new_page()

        console_logs = []
        errors = []

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        try:
            # 1. Navigate
            print("\n1. Navigating to localhost:3000...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"   ✓ Page loaded: {page.title()}")
            print(f"   ✓ URL: {page.url}")

            page.wait_for_timeout(2000)

            # 2. Check page structure
            print("\n2. Checking page structure...")
            has_form = page.locator("#scrapeForm").count() > 0
            has_scrape_btn = page.locator("#scrapeBtn").count() > 0
            has_cache_toggle = page.locator('[data-testid="cache-toggle-input"]').count() > 0

            print(f"   ✓ Scrape form: {has_form}")
            print(f"   ✓ Scrape button: {has_scrape_btn}")
            print(f"   ✓ Cache toggle: {has_cache_toggle}")

            if not all([has_form, has_scrape_btn, has_cache_toggle]):
                print("   ❌ Missing elements!")
                page.screenshot(path="/tmp/local_missing.png")
                print(f"   📸 Screenshot: /tmp/local_missing.png")

                # Debug: print HTML
                html = page.content()
                print(f"\n   HTML length: {len(html)} chars")
                print(f"   First 500 chars:\n{html[:500]}")
                return

            # 3. Check form state
            print("\n3. Checking form state...")
            start_date = page.input_value("#start_date")
            end_date = page.input_value("#end_date")
            cache_enabled = page.is_checked('[data-testid="cache-toggle-input"]')

            print(f"   ✓ Start date: {start_date}")
            print(f"   ✓ End date: {end_date}")
            print(f"   ✓ Cache enabled: {cache_enabled}")

            # 4. Screenshot before
            page.screenshot(path="/tmp/local_before.png")
            print("\n4. 📸 Screenshot saved: /tmp/local_before.png")

            # 5. Click scrape
            print("\n5. Clicking scrape button...")
            btn_text_before = page.locator("#scrapeBtn").text_content()
            print(f"   ✓ Button text before: '{btn_text_before}'")

            page.click("#scrapeBtn")
            page.wait_for_timeout(2000)

            btn_text_during = page.locator("#scrapeBtn").text_content()
            print(f"   ✓ Button text during: '{btn_text_during}'")

            # 6. Wait for results
            print("\n6. Waiting for scrape to complete (up to 90s)...")

            try:
                page.wait_for_selector(
                    ".article-card, button:has-text('Scrape Newsletters')",
                    timeout=90000
                )
                print("   ✅ Scraping completed!")
            except Exception as e:
                print(f"   ⚠ Timeout: {e}")
                page.screenshot(path="/tmp/local_timeout.png")
                print(f"   📸 Screenshot: /tmp/local_timeout.png")

                if errors:
                    print("\n   🔴 Page errors:")
                    for err in errors:
                        print(f"      {err}")

                return

            # 7. Check DOM updates
            print("\n7. Checking DOM updates...")

            article_count = page.locator(".article-card").count()
            has_result = page.locator("#result").count() > 0
            has_stats = page.locator(".stats").count() > 0

            print(f"   ✓ Articles: {article_count}")
            print(f"   ✓ Result div: {has_result}")
            print(f"   ✓ Stats div: {has_stats}")

            if article_count > 0:
                print("   ✅ SUCCESS! Articles rendered!")
                page.screenshot(path="/tmp/local_success.png")
                print(f"   📸 Screenshot: /tmp/local_success.png")
            else:
                print("   ⚠ No articles found")
                page.screenshot(path="/tmp/local_no_articles.png")
                print(f"   📸 Screenshot: /tmp/local_no_articles.png")

                if has_stats:
                    stats_text = page.locator(".stats").text_content()
                    print(f"   ℹ Stats: {stats_text}")

            # 8. Check localStorage
            print("\n8. Checking localStorage...")
            storage_keys = page.evaluate("""
                () => {
                    const keys = []
                    for (let i = 0; i < localStorage.length; i++) {
                        keys.push(localStorage.key(i))
                    }
                    return keys
                }
            """)

            print(f"   ℹ localStorage keys: {storage_keys if storage_keys else '(empty)'}")

            newsletter_keys = [k for k in storage_keys if k.startswith('newsletters:scrapes:')]
            if newsletter_keys:
                print(f"   ⚠ Found newsletter keys (should use Supabase): {newsletter_keys}")
            else:
                print("   ✅ No newsletter keys (correct for Phase 5!)")

            # 9. Test interactions
            if article_count > 0:
                print("\n9. Testing article interactions...")

                first_article = page.locator(".article-card").first
                article_classes = first_article.get_attribute("class")
                print(f"   ✓ Article classes: {article_classes}")

                # Hover
                first_article.hover()
                page.wait_for_timeout(500)

                has_tldr = first_article.locator(".tldr-btn").count() > 0
                has_remove = first_article.locator(".remove-article-btn").count() > 0

                print(f"   ✓ TLDR button: {has_tldr}")
                print(f"   ✓ Remove button: {has_remove}")

                if has_remove:
                    # Test remove
                    print("\n   🔄 Testing remove button...")
                    classes_before = first_article.get_attribute("class")

                    first_article.locator(".remove-article-btn").click()
                    page.wait_for_timeout(1000)

                    classes_after = first_article.get_attribute("class")

                    print(f"      Before: {classes_before}")
                    print(f"      After:  {classes_after}")

                    if "removed" in classes_after and "removed" not in classes_before:
                        print("      ✅ Remove worked!")
                        page.screenshot(path="/tmp/local_removed.png")
                        print(f"      📸 Screenshot: /tmp/local_removed.png")
                    else:
                        print("      ⚠ Remove may not have worked")

            # 10. Check errors
            print("\n10. Checking for errors...")
            if errors:
                print(f"   🔴 Page errors ({len(errors)}):")
                for err in errors:
                    print(f"      {err}")
            else:
                print("   ✅ No page errors!")

            # 11. Console logs
            print("\n11. Console logs...")
            error_logs = [log for log in console_logs if '[error]' in log.lower() or '[warning]' in log.lower()]
            if error_logs:
                print(f"   ⚠ Errors/warnings ({len(error_logs)}):")
                for log in error_logs[:5]:
                    print(f"      {log}")
            else:
                print("   ✅ No error logs")

            storage_logs = [log for log in console_logs if 'storage' in log.lower() or 'supabase' in log.lower()]
            if storage_logs:
                print(f"\n   ℹ Storage-related logs ({len(storage_logs)}):")
                for log in storage_logs[:5]:
                    print(f"      {log}")

            # 12. Final screenshot
            print("\n12. Final screenshot...")
            page.screenshot(path="/tmp/local_final.png", full_page=True)
            print(f"   📸 Saved: /tmp/local_final.png")

            # 13. Network activity
            print("\n13. Analyzing network activity...")
            print("   (Network monitoring not enabled - would need to setup route handlers)")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            page.screenshot(path="/tmp/local_error.png")
            print(f"   📸 Error screenshot: /tmp/local_error.png")

            import traceback
            traceback.print_exc()

        finally:
            browser.close()

        print("\n" + "="*80)
        print("✓ LOCAL TEST COMPLETED")
        print("="*80)

        # Summary
        print("\n📊 SUMMARY:")
        print(f"  - Page loaded: {'✓' if has_form else '✗'}")
        print(f"  - Scrape completed: {'✓' if article_count > 0 else '✗'}")
        print(f"  - Articles rendered: {article_count}")
        print(f"  - Page errors: {len(errors)}")
        print(f"  - Console errors: {len(error_logs) if 'error_logs' in locals() else 0}")
        print(f"  - localStorage keys: {len(storage_keys) if 'storage_keys' in locals() else 0}")

        print("\n📸 Screenshots:")
        print("  - /tmp/local_before.png")
        print("  - /tmp/local_success.png or /tmp/local_no_articles.png")
        print("  - /tmp/local_removed.png (if remove tested)")
        print("  - /tmp/local_final.png")


if __name__ == "__main__":
    test_local_phase5_aggressive()
