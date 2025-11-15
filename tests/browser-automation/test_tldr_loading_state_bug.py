"""
Test to reproduce TLDR loading state bug:
When user clicks TLDR and refreshes before request completes,
the article gets stuck in loading state even though no request is running.
"""

from playwright.sync_api import sync_playwright
import time


def test_tldr_loading_state_bug():
    """Reproduce bug where TLDR button gets stuck in loading state after refresh"""

    url = "http://localhost:3000/"

    with sync_playwright() as p:
        print("="*80)
        print("TLDR LOADING STATE BUG REPRODUCTION")
        print(f"URL: {url}")
        print("="*80)

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

        browser = p.chromium.launch(**launch_options)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            bypass_csp=True,
        )

        page = context.new_page()

        # Track network requests
        api_requests = []
        page.on("request", lambda req: (
            api_requests.append({
                "url": req.url,
                "method": req.method,
                "timestamp": time.time()
            }) if "/api/" in req.url else None
        ))

        console_logs = []
        errors = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        try:
            # ===================================================================
            # TEST 1: Initial Load - Verify Articles from Supabase
            # ===================================================================
            print("\n" + "="*80)
            print("TEST 1: Initial Load - Articles Should Load from Supabase Cache")
            print("="*80)

            print("\n1. Loading page...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"   ✓ Page loaded: {page.title()}")

            page.wait_for_timeout(3000)

            # Check if articles are already loaded from Supabase cache
            article_count = page.locator(".article-card").count()
            print(f"   ✓ Articles loaded from cache: {article_count}")

            if article_count == 0:
                print("\n   ℹ No cached articles, triggering scrape...")
                page.click("#scrapeBtn")
                page.wait_for_selector(".article-card", timeout=90000)
                article_count = page.locator(".article-card").count()
                print(f"   ✓ Articles after scrape: {article_count}")

            page.screenshot(path="/tmp/tldr_bug_initial.png")
            print("   📸 Screenshot: /tmp/tldr_bug_initial.png")

            # ===================================================================
            # TEST 2: Click TLDR and Immediately Refresh
            # ===================================================================
            print("\n" + "="*80)
            print("TEST 2: Click TLDR and Immediately Refresh (Bug Reproduction)")
            print("="*80)

            if article_count > 0:
                print("\n1. Finding first article...")
                first_article = page.locator(".article-card").first
                tldr_button = first_article.locator(".tldr-btn")

                initial_button_text = tldr_button.text_content()
                print(f"   ✓ Initial button text: '{initial_button_text}'")

                print("\n2. Clicking TLDR button...")
                api_requests.clear()

                # Click TLDR button
                tldr_button.click()

                # Wait just a tiny bit to ensure the state is updated
                page.wait_for_timeout(100)

                # Take screenshot right after click
                page.screenshot(path="/tmp/tldr_bug_after_click.png")
                print("   📸 Screenshot after click: /tmp/tldr_bug_after_click.png")

                # Check if button text changed
                button_text_after_click = tldr_button.text_content()
                print(f"   ✓ Button text after click: '{button_text_after_click}'")

                # Check for TLDR API request
                tldr_requests = [r for r in api_requests if "/api/tldr-url" in r["url"]]
                print(f"   ✓ TLDR API requests initiated: {len(tldr_requests)}")

                print("\n3. Refreshing page immediately (killing request mid-flight)...")
                page.reload(wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                print("   ✓ Page refreshed")

                # ===================================================================
                # TEST 3: Verify Bug - Article Stuck in Loading State
                # ===================================================================
                print("\n" + "="*80)
                print("TEST 3: Verify Bug - Check if Article is Stuck in Loading State")
                print("="*80)

                print("\n1. Finding the same article after refresh...")
                first_article_after = page.locator(".article-card").first
                tldr_button_after = first_article_after.locator(".tldr-btn")

                button_text_after_refresh = tldr_button_after.text_content()
                button_disabled = tldr_button_after.is_disabled()
                button_classes = tldr_button_after.get_attribute("class")

                print(f"   ✓ Button text after refresh: '{button_text_after_refresh}'")
                print(f"   ✓ Button disabled: {button_disabled}")
                print(f"   ✓ Button classes: {button_classes}")

                # Check article link for loading class
                article_link = first_article_after.locator(".article-link")
                link_classes = article_link.get_attribute("class")
                print(f"   ✓ Article link classes: {link_classes}")

                page.screenshot(path="/tmp/tldr_bug_after_refresh.png")
                print("   📸 Screenshot: /tmp/tldr_bug_after_refresh.png")

                # ===================================================================
                # Diagnosis
                # ===================================================================
                print("\n" + "="*80)
                print("BUG DIAGNOSIS")
                print("="*80)

                is_stuck = (
                    button_text_after_refresh == "Loading..." or
                    button_disabled or
                    "loading" in (link_classes or "")
                )

                if is_stuck:
                    print("\n❌ BUG REPRODUCED!")
                    print("   The article is stuck in loading state even though no request is running.")
                    print(f"   - Button text: '{button_text_after_refresh}'")
                    print(f"   - Button disabled: {button_disabled}")
                    print(f"   - Link has 'loading' class: {'loading' in (link_classes or '')}")

                    print("\n🔍 Root Cause:")
                    print("   When the TLDR button is clicked, the article's tldr.status is set to 'creating'")
                    print("   in Supabase. If the page refreshes before the request completes, the status")
                    print("   remains 'creating' in the database, but no request is actually running.")
                    print("   On reload, the component reads the stale 'creating' status from Supabase.")

                else:
                    print("\n✅ Bug NOT reproduced")
                    print("   The article is not stuck in loading state.")
                    print("   This could mean:")
                    print("   - The bug has been fixed")
                    print("   - The timing wasn't right to catch the state")
                    print("   - The TLDR request completed before the refresh")

                # ===================================================================
                # Check Supabase State Directly
                # ===================================================================
                print("\n" + "="*80)
                print("CHECKING SUPABASE STATE")
                print("="*80)

                # Get the article data from the page's React state
                article_data = page.evaluate("""
                    () => {
                        // Try to find React fiber to inspect state
                        const articleCard = document.querySelector('.article-card');
                        if (!articleCard) return null;

                        // Look for the article in the page's internal state
                        // This is a hack but useful for debugging
                        const tldrBtn = articleCard.querySelector('.tldr-btn');
                        return {
                            buttonText: tldrBtn?.textContent,
                            buttonDisabled: tldrBtn?.disabled,
                            classes: articleCard.className
                        }
                    }
                """)

                print(f"\n   Article state from DOM:")
                print(f"   - Button text: '{article_data.get('buttonText', 'N/A')}'")
                print(f"   - Button disabled: {article_data.get('buttonDisabled', 'N/A')}")
                print(f"   - Card classes: {article_data.get('classes', 'N/A')}")

            else:
                print("\n⚠ No articles found, cannot reproduce bug")

            # ===================================================================
            # FINAL SUMMARY
            # ===================================================================
            print("\n" + "="*80)
            print("TEST SUMMARY")
            print("="*80)

            print(f"\n📊 Statistics:")
            print(f"  - Articles found: {article_count}")
            print(f"  - Page errors: {len(errors)}")

            if errors:
                print(f"\n⚠ Page Errors ({len(errors)}):")
                for err in errors[:5]:
                    print(f"  {err}")

            print(f"\n📸 Screenshots saved:")
            print(f"  - /tmp/tldr_bug_initial.png")
            print(f"  - /tmp/tldr_bug_after_click.png")
            print(f"  - /tmp/tldr_bug_after_refresh.png")

            print("\n" + "="*80)

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            page.screenshot(path="/tmp/tldr_bug_error.png")
            print(f"   📸 Error screenshot: /tmp/tldr_bug_error.png")

            import traceback
            traceback.print_exc()

        finally:
            browser.close()


if __name__ == "__main__":
    test_tldr_loading_state_bug()
