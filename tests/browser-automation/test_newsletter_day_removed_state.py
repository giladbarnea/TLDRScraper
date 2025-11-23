import time
from playwright.sync_api import sync_playwright, expect

def test_newsletter_day_removed_state():
    """Test that when all articles in a newsletter category are removed, the category shows a removed state"""

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

        page.screenshot(path='/tmp/1_initial_load.png')

        start_date_input = page.locator('input[type="date"]').first
        end_date_input = page.locator('input[type="date"]').last

        start_date_input.fill('2024-11-20')
        end_date_input.fill('2024-11-20')

        scrape_button = page.get_by_role('button', name='Scrape')
        scrape_button.click()

        time.sleep(8)
        page.screenshot(path='/tmp/2_after_scrape.png')

        simon_willison_heading = page.locator('h3:has-text("Simon Willison")').first
        expect(simon_willison_heading).to_be_visible()

        initial_classes = simon_willison_heading.get_attribute('class')
        print(f"Initial category heading classes: {initial_classes}")
        assert 'line-through' not in initial_classes, "Category should not be strikethrough initially"

        simon_section = simon_willison_heading.locator('xpath=ancestor::div[contains(@class, "space-y-6")]').first
        trash_buttons = simon_section.locator('button:has(svg)').filter(has=page.locator('svg'))

        article_count = trash_buttons.count()
        print(f"Found {article_count} articles in Simon Willison section")

        for i in range(article_count):
            trash_button = trash_buttons.nth(i)
            trash_button.click()
            time.sleep(0.5)

        time.sleep(2)
        page.screenshot(path='/tmp/3_all_articles_removed.png')

        updated_classes = simon_willison_heading.get_attribute('class')
        print(f"Updated category heading classes: {updated_classes}")

        assert 'line-through' in updated_classes, "Category heading should have line-through when all articles removed"
        assert 'text-slate-400' in updated_classes, "Category heading should be grayed out when all articles removed"

        category_border = simon_willison_heading.locator('xpath=parent::div').first
        border_classes = category_border.get_attribute('class')
        print(f"Category border classes: {border_classes}")
        assert 'opacity-50' in border_classes, "Category section should have reduced opacity when all articles removed"

        print("✅ Newsletter day removed state test passed!")

        browser.close()

if __name__ == '__main__':
    test_newsletter_day_removed_state()
