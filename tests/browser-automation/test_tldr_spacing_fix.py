import time
from playwright.sync_api import sync_playwright

def test_tldr_spacing():
    with sync_playwright() as p:
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

        page.goto('http://localhost:5001', wait_until='domcontentloaded')
        page.wait_for_selector('body', state='visible')
        time.sleep(3)

        start_date = page.locator('input[type="date"]').first
        end_date = page.locator('input[type="date"]').last

        start_date.fill('2025-11-20')
        end_date.fill('2025-11-20')

        page.locator('button:has-text("Scrape")').click()

        time.sleep(8)

        page.screenshot(path='/tmp/tldr_spacing_collapsed.png', full_page=True)
        print("Screenshot saved: /tmp/tldr_spacing_collapsed.png")

        tldr_buttons = page.locator('button:has-text("TLDR")').all()
        if len(tldr_buttons) > 0:
            tldr_buttons[0].click()
            time.sleep(3)

            page.screenshot(path='/tmp/tldr_spacing_expanded.png', full_page=True)
            print("Screenshot saved: /tmp/tldr_spacing_expanded.png")

            tldr_buttons[0].click()
            time.sleep(1)

            page.screenshot(path='/tmp/tldr_spacing_collapsed_after.png', full_page=True)
            print("Screenshot saved: /tmp/tldr_spacing_collapsed_after.png")

        browser.close()

if __name__ == '__main__':
    test_tldr_spacing()
