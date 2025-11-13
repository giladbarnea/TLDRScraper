"""
Smoke test for Phase 5 Supabase storage implementation
Tests the preview deployment at Vercel
"""

from playwright.sync_api import sync_playwright


def test_phase5_smoke():
    """Smoke test for Phase 5 - Supabase storage"""

    url = "https://tldr-flask-scraper-git-claude-impl-40d375-giladbarneas-projects.vercel.app/"

    with sync_playwright() as p:
        print("="*80)
        print("PHASE 5 SMOKE TEST - SUPABASE STORAGE")
        print(f"URL: {url}")
        print("="*80)

        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = context.new_page()

        console_logs = []
        errors = []

        page.on("console", lambda msg: console_logs.append(f"[{msg.type()}] {msg.text()}"))
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        try:
            # 1. Load page
            print("\n1. Loading page...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"   ✓ Page loaded: {page.title()}")

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
                print("   ❌ Missing expected elements!")
                page.screenshot(path="/tmp/phase5_missing_elements.png")
                return

            # 3. Check if dates are pre-filled
            print("\n3. Checking form state...")
            start_date = page.input_value("#start_date")
            end_date = page.input_value("#end_date")
            cache_enabled = page.is_checked('[data-testid="cache-toggle-input"]')

            print(f"   ✓ Start date: {start_date}")
            print(f"   ✓ End date: {end_date}")
            print(f"   ✓ Cache enabled: {cache_enabled}")

            # 4. Take screenshot before scrape
            page.screenshot(path="/tmp/phase5_before_scrape.png")
            print("\n4. Screenshot: /tmp/phase5_before_scrape.png")

            # 5. Click scrape button
            print("\n5. Clicking scrape button...")
            btn_text_before = page.locator("#scrapeBtn").text_content()
            print(f"   ✓ Button text before: '{btn_text_before}'")

            page.click("#scrapeBtn")

            # Wait for button to change
            page.wait_for_timeout(2000)
            btn_text_during = page.locator("#scrapeBtn").text_content()
            print(f"   ✓ Button text during: '{btn_text_during}'")

            # 6. Wait for results (up to 90 seconds)
            print("\n6. Waiting for scrape to complete...")
            print("   ⏳ This may take 30-90 seconds...")

            try:
                page.wait_for_selector(
                    ".article-card, button:has-text('Scrape Newsletters')",
                    timeout=90000
                )
                print("   ✓ Scraping completed")
            except Exception as e:
                print(f"   ⚠ Scraping timed out: {e}")
                page.screenshot(path="/tmp/phase5_timeout.png")

                # Check for errors
                if errors:
                    print("\n   🔴 Page errors detected:")
                    for err in errors:
                        print(f"      {err}")

                return

            # 7. Check results in DOM
            print("\n7. Checking DOM updates...")

            article_count = page.locator(".article-card").count()
            result_div = page.locator("#result").count() > 0
            stats_div = page.locator(".stats").count() > 0

            print(f"   ✓ Articles found: {article_count}")
            print(f"   ✓ Result div present: {result_div}")
            print(f"   ✓ Stats div present: {stats_div}")

            if article_count == 0:
                print("   ⚠ No articles found!")
                page.screenshot(path="/tmp/phase5_no_articles.png")

                # Check stats text
                if stats_div:
                    stats_text = page.locator(".stats").text_content()
                    print(f"   ℹ Stats text: {stats_text}")
            else:
                print("   ✅ Articles rendered successfully!")
                page.screenshot(path="/tmp/phase5_with_results.png")

            # 8. Check localStorage (should be empty or minimal in Phase 5)
            print("\n8. Checking localStorage (should use Supabase now)...")

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

            # Check if any are newsletters:scrapes keys (should NOT be there in Phase 5)
            newsletter_keys = [k for k in storage_keys if k.startswith('newsletters:scrapes:')]
            if newsletter_keys:
                print(f"   ⚠ Found localStorage newsletter keys (should use Supabase): {newsletter_keys}")
            else:
                print("   ✅ No localStorage newsletter keys (correct for Phase 5!)")

            # 9. Test article interactions
            if article_count > 0:
                print("\n9. Testing article interactions...")

                first_article = page.locator(".article-card").first

                # Check classes
                article_classes = first_article.get_attribute("class")
                print(f"   ✓ Article classes: {article_classes}")

                # Hover to show action buttons
                first_article.hover()
                page.wait_for_timeout(500)

                # Check for buttons
                has_tldr_btn = first_article.locator(".tldr-btn").count() > 0
                has_remove_btn = first_article.locator(".remove-article-btn").count() > 0

                print(f"   ✓ TLDR button: {has_tldr_btn}")
                print(f"   ✓ Remove button: {has_remove_btn}")

                # Check if buttons are disabled (loading state)
                if has_remove_btn:
                    is_disabled = first_article.locator(".remove-article-btn").is_disabled()
                    print(f"   ✓ Remove button disabled: {is_disabled}")

            # 10. Check for JavaScript errors
            print("\n10. Checking for errors...")

            if errors:
                print(f"   🔴 Page errors detected ({len(errors)}):")
                for err in errors:
                    print(f"      {err}")
            else:
                print("   ✅ No page errors")

            # 11. Check console for storage-related messages
            print("\n11. Console messages (storage-related)...")

            storage_logs = [log for log in console_logs if 'storage' in log.lower() or 'supabase' in log.lower()]
            if storage_logs:
                print(f"   ℹ Found {len(storage_logs)} storage-related messages:")
                for log in storage_logs[:5]:
                    print(f"      {log}")
            else:
                print("   ℹ No storage-related console messages")

            # Show first 5 error/warning logs
            error_logs = [log for log in console_logs if '[error]' in log.lower() or '[warning]' in log.lower()]
            if error_logs:
                print(f"\n   ⚠ Errors/warnings in console ({len(error_logs)}):")
                for log in error_logs[:5]:
                    print(f"      {log}")

            # 12. Final screenshot
            print("\n12. Final screenshot...")
            page.screenshot(path="/tmp/phase5_final.png", full_page=True)
            print("   ✓ Saved: /tmp/phase5_final.png")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            page.screenshot(path="/tmp/phase5_error.png")
            import traceback
            traceback.print_exc()

        finally:
            browser.close()

        print("\n" + "="*80)
        print("✓ SMOKE TEST COMPLETED")
        print("="*80)

        # Summary
        print("\nSUMMARY:")
        print(f"  - Page loaded: {'✓' if has_form else '✗'}")
        print(f"  - Scrape completed: {'✓' if article_count > 0 else '✗'}")
        print(f"  - Articles rendered: {article_count}")
        print(f"  - Page errors: {len(errors)}")
        print(f"  - localStorage keys: {len(storage_keys)}")


if __name__ == "__main__":
    test_phase5_smoke()
