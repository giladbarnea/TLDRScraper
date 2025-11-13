"""
Final comprehensive Phase 5 test - single run, all browsers
"""

from playwright.sync_api import sync_playwright


def test_with_browser(browser_type_name, playwright_obj):
    """Run test with specific browser"""

    print(f"\n{'='*80}")
    print(f"Testing with {browser_type_name.upper()}")
    print(f"{'='*80}")

    browser_type = getattr(playwright_obj, browser_type_name)

    try:
        browser = browser_type.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox'] if browser_type_name == 'chromium' else None
        )
    except Exception as e:
        print(f"❌ Failed to launch {browser_type_name}: {e}")
        return False

    try:
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        # Navigate
        print("\n1. Loading http://localhost:3000...")
        page.goto("http://localhost:3000/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)  # Wait for React
        print(f"   ✓ Page: {page.title()}")

        # Check structure
        print("\n2. Checking structure...")
        has_form = page.locator("#scrapeForm").count() > 0
        has_btn = page.locator("#scrapeBtn").count() > 0
        has_toggle = page.locator('[data-testid="cache-toggle-input"]').count() > 0

        print(f"   Form: {has_form}, Button: {has_btn}, Toggle: {has_toggle}")

        if not all([has_form, has_btn, has_toggle]):
            print("   ❌ Missing elements!")
            return False

        # Check pre-filled dates
        start = page.input_value("#start_date")
        end = page.input_value("#end_date")
        cache = page.is_checked('[data-testid="cache-toggle-input"]')
        print(f"   Dates: {start} to {end}, Cache: {cache}")

        # Screenshot before
        page.screenshot(path=f"/tmp/{browser_type_name}_before.png")
        print(f"   📸 Saved: /tmp/{browser_type_name}_before.png")

        # Click scrape
        print("\n3. Scraping newsletters...")
        btn_before = page.locator("#scrapeBtn").text_content()
        print(f"   Button: '{btn_before}'")

        page.click("#scrapeBtn")
        page.wait_for_timeout(2000)

        btn_during = page.locator("#scrapeBtn").text_content()
        print(f"   Button: '{btn_during}'")

        # Wait for completion
        print("   ⏳ Waiting up to 90s...")
        try:
            page.wait_for_selector(
                ".article-card, button:has-text('Scrape Newsletters')",
                timeout=90000
            )
            print("   ✅ Completed!")
        except Exception as e:
            print(f"   ⚠ Timeout: {e}")
            page.screenshot(path=f"/tmp/{browser_type_name}_timeout.png")
            return False

        # Check results
        print("\n4. Checking results...")
        article_count = page.locator(".article-card").count()
        has_result = page.locator("#result").count() > 0
        has_stats = page.locator(".stats").count() > 0

        print(f"   Articles: {article_count}")
        print(f"   Result div: {has_result}")
        print(f"   Stats div: {has_stats}")

        if has_stats:
            stats_text = page.locator(".stats").text_content()
            print(f"   Stats: {stats_text[:100]}")

        # Check localStorage
        print("\n5. Checking localStorage...")
        storage_keys = page.evaluate("() => Object.keys(localStorage)")
        print(f"   Keys: {storage_keys if storage_keys else '(empty)'}")

        newsletter_keys = [k for k in storage_keys if 'newsletters:scrapes:' in k]
        if newsletter_keys:
            print(f"   ⚠ Newsletter keys found: {newsletter_keys}")
        else:
            print("   ✅ No newsletter keys (correct!)")

        # Screenshot after
        page.screenshot(path=f"/tmp/{browser_type_name}_after.png", full_page=True)
        print(f"   📸 Saved: /tmp/{browser_type_name}_after.png")

        # Console errors
        print("\n6. Console logs...")
        errors = [log for log in console_logs if 'error' in log.lower()]
        if errors:
            print(f"   ⚠ Errors ({len(errors)}):")
            for err in errors[:3]:
                print(f"      {err}")
        else:
            print("   ✅ No errors")

        # Summary for this browser
        print(f"\n📊 {browser_type_name.upper()} SUMMARY:")
        print(f"   Page loaded: ✓")
        print(f"   Scrape completed: ✓")
        print(f"   Articles rendered: {article_count}")
        print(f"   localStorage clean: {'✓' if not newsletter_keys else '✗'}")
        print(f"   Console errors: {len(errors)}")

        browser.close()
        return article_count > 0

    except Exception as e:
        print(f"\n❌ {browser_type_name} ERROR: {e}")
        import traceback
        traceback.print_exc()
        try:
            page.screenshot(path=f"/tmp/{browser_type_name}_error.png")
        except:
            pass
        browser.close()
        return False


def main():
    """Test Phase 5 with all available browsers"""

    print("="*80)
    print("PHASE 5 COMPREHENSIVE LOCAL TEST")
    print("Testing: http://localhost:3000/")
    print("="*80)

    with sync_playwright() as p:
        results = {}

        # Try Chromium
        results['chromium'] = test_with_browser('chromium', p)

        # Try Firefox
        results['firefox'] = test_with_browser('firefox', p)

        # Final summary
        print("\n" + "="*80)
        print("FINAL RESULTS")
        print("="*80)

        for browser, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{browser.upper()}: {status}")

        print("\n📸 All screenshots saved to /tmp/")
        print("   chromium_before.png, chromium_after.png")
        print("   firefox_before.png, firefox_after.png")

        # Overall verdict
        any_passed = any(results.values())
        if any_passed:
            print("\n✅ Phase 5 is WORKING! (at least one browser passed)")
        else:
            print("\n❌ Phase 5 has ISSUES (all browsers failed)")


if __name__ == "__main__":
    main()
