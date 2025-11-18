import time
import os
from playwright.sync_api import sync_playwright

def test_vercel_deployment():
    """Test the Vercel deployment at the given URL"""
    url = "https://tldr-flask-scraper-git-claude-hide-d1c7ab-giladbarneas-projects.vercel.app/"

    proxy_server = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')

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

    if proxy_server:
        launch_options['proxy'] = {'server': proxy_server}
        print(f"Using proxy: {proxy_server}")

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_options)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            bypass_csp=True,
        )
        page = context.new_page()

        console_messages = []
        page_errors = []
        network_requests = []

        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("request", lambda req: network_requests.append(f"{req.method} {req.url}"))

        print(f"\n=== Navigating to {url} ===")
        page.goto(url, wait_until="domcontentloaded")

        page.wait_for_selector('body', state="visible")
        print("✓ Page body visible")

        time.sleep(3)

        initial_screenshot = "/tmp/vercel_initial.png"
        page.screenshot(path=initial_screenshot)
        print(f"✓ Screenshot saved to {initial_screenshot}")

        print("\n=== Page Title ===")
        print(page.title())

        print("\n=== Checking for key UI elements ===")

        try:
            scrape_form = page.query_selector('.scrape-form, form, [class*="scrape"]')
            if scrape_form:
                print("✓ Found scrape form element")
            else:
                print("⚠ No scrape form found")
        except Exception as e:
            print(f"⚠ Error checking scrape form: {e}")

        try:
            cache_toggle = page.query_selector('[type="checkbox"], .cache-toggle, [class*="cache"]')
            if cache_toggle:
                print("✓ Found cache toggle element")
            else:
                print("⚠ No cache toggle found")
        except Exception as e:
            print(f"⚠ Error checking cache toggle: {e}")

        try:
            date_inputs = page.query_selector_all('input[type="date"]')
            print(f"✓ Found {len(date_inputs)} date input(s)")
        except Exception as e:
            print(f"⚠ Error checking date inputs: {e}")

        try:
            buttons = page.query_selector_all('button')
            print(f"✓ Found {len(buttons)} button(s)")
            for i, btn in enumerate(buttons[:5]):
                text = btn.inner_text() if btn.is_visible() else "[hidden]"
                print(f"  - Button {i+1}: {text}")
        except Exception as e:
            print(f"⚠ Error checking buttons: {e}")

        print("\n=== Console Messages (first 10) ===")
        for msg in console_messages[:10]:
            print(msg)

        if page_errors:
            print("\n=== Page Errors ===")
            for err in page_errors:
                print(err)

        print("\n=== Network Requests (first 20) ===")
        for req in network_requests[:20]:
            print(req)

        print("\n=== Testing scrape form interaction ===")
        try:
            start_date_input = page.query_selector('input[type="date"]')
            if start_date_input:
                start_date_input.fill('2025-11-15')
                print("✓ Filled start date with 2025-11-15")

                time.sleep(1)

                date_inputs_all = page.query_selector_all('input[type="date"]')
                if len(date_inputs_all) >= 2:
                    end_date_input = date_inputs_all[1]
                    end_date_input.fill('2025-11-17')
                    print("✓ Filled end date with 2025-11-17")

                time.sleep(1)

                after_dates_screenshot = "/tmp/vercel_after_dates.png"
                page.screenshot(path=after_dates_screenshot)
                print(f"✓ Screenshot saved to {after_dates_screenshot}")

                scrape_button = page.query_selector('button:has-text("Scrape")')
                if not scrape_button:
                    scrape_button = page.query_selector('button[type="submit"]')

                if scrape_button and scrape_button.is_visible():
                    print("✓ Found scrape button, attempting click...")
                    scrape_button.click()
                    print("✓ Clicked scrape button")

                    time.sleep(5)

                    after_scrape_screenshot = "/tmp/vercel_after_scrape.png"
                    page.screenshot(path=after_scrape_screenshot)
                    print(f"✓ Screenshot saved to {after_scrape_screenshot}")

                    results = page.query_selector('.results, [class*="result"]')
                    if results:
                        print("✓ Found results element")
                    else:
                        print("⚠ No results element found")
                else:
                    print("⚠ Scrape button not found or not visible")
        except Exception as e:
            print(f"⚠ Error testing scrape form: {e}")

        print("\n=== Final Console Messages ===")
        for msg in console_messages[-10:]:
            print(msg)

        print("\n=== Test Complete ===")

        browser.close()

if __name__ == "__main__":
    test_vercel_deployment()
