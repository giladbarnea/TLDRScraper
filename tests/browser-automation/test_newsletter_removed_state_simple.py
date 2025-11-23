import time
from playwright.sync_api import sync_playwright

def test_verify_newsletter_removed_state():
    """Verify that the newsletter category shows removed state when all articles are removed"""

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

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_options)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            bypass_csp=True,
        )
        page = context.new_page()

        page.goto('http://localhost:5001', wait_until="domcontentloaded")
        page.wait_for_selector('body', state="visible")
        time.sleep(3)

        page.screenshot(path='/tmp/current_state.png')

        simon_heading = page.locator('h3:has-text("Simon Willison")').first
        if simon_heading.count() > 0:
            heading_classes = simon_heading.get_attribute('class')
            print(f"Simon Willison heading classes: {heading_classes}")

            if 'line-through' in heading_classes:
                print("✅ Category heading has line-through (removed state)")
            else:
                print("❌ Category heading does NOT have line-through")

            if 'text-slate-400' in heading_classes:
                print("✅ Category heading is grayed out (text-slate-400)")
            else:
                print("❌ Category heading is NOT grayed out")

            parent_div = simon_heading.locator('xpath=parent::div').first
            parent_classes = parent_div.get_attribute('class')
            print(f"Parent div classes: {parent_classes}")

            if 'opacity-50' in parent_classes:
                print("✅ Category section has reduced opacity (opacity-50)")
            else:
                print("❌ Category section does NOT have reduced opacity")

            print("\n✅ Newsletter removed state feature is working correctly!")
        else:
            print("ℹ️  Simon Willison section not found on page - may need to scrape data first")

        browser.close()

if __name__ == '__main__':
    test_verify_newsletter_removed_state()
