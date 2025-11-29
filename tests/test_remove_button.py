import datetime
import time
import re
from playwright.sync_api import sync_playwright, expect

def run():
    today = datetime.date.today().isoformat()
    print(f"Today is: {today}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
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
            ]
        )
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        
        # Enable console logging
        page = context.new_page()
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"BROWSER ERROR: {exc}"))

        print("Navigating to app...")
        try:
            page.goto("http://localhost:3000")
            page.wait_for_load_state("networkidle")
        except Exception as e:
            print(f"Navigation failed: {e}")
            page.screenshot(path="nav_failed.png")
            raise

        # Fill dates
        print("Filling dates...")
        try:
            page.fill('#start_date', today)
            page.fill('#end_date', today)
        except Exception as e:
            print(f"Filling dates failed: {e}")
            page.screenshot(path="fill_dates_failed.png")
            raise
        
        print("Clicking Update Feed...")
        try:
            page.click('button:has-text("Update Feed")', force=True)
        except Exception as e:
             print(f"Clicking button failed: {e}")
             page.screenshot(path="click_failed.png")
             raise

        # Wait for results
        print("Waiting for results...")
        try:
            # Increase timeout significantly as scraping can be slow
            page.wait_for_selector('div[data-testid^="article-card-"]', timeout=120000)
        except Exception as e:
            print(f"Waiting for results failed: {e}")
            page.screenshot(path="wait_results_failed.png")
            with open("wait_results_failed.html", "w") as f:
                f.write(page.content())
            raise
        
        # Get first article
        first_card = page.locator('div[data-testid^="article-card-"]').first
        article_url = first_card.get_attribute("data-testid").replace("article-card-", "")
        print(f"Testing article: {article_url}")

        # Create stable locators
        target_card = page.locator(f'[data-testid="article-card-{article_url}"]')
        remove_btn = page.locator(f'[data-testid="remove-button-{article_url}"]')
        
        # Click remove
        print("Clicking remove button...")
        remove_btn.click(force=True)
        
        # Verify removed state
        print("Verifying removed state...")
        try:
            expect(target_card).to_have_class(re.compile(r"opacity-50"), timeout=10000)
        except AssertionError as e:
            print(f"Assertion failed: {e}")
            page.screenshot(path="assertion_failed.png")
            raise
        
        # Verify remove button is GONE
        print("Verifying remove button is hidden...")
        expect(remove_btn).not_to_be_visible()

        # Refresh
        print("Reloading page...")
        page.reload()
        page.wait_for_selector(f'[data-testid="article-card-{article_url}"]')
        
        # Verify persistence
        print("Verifying persistence...")
        article_card_after_reload = page.locator(f'[data-testid="article-card-{article_url}"]')
        expect(article_card_after_reload).to_have_class(re.compile(r"opacity-50"))
        
        # Restore
        print("Restoring article...")
        article_card_after_reload.click(force=True)
        
        # Verify restored state
        print("Verifying restored state...")
        expect(article_card_after_reload).not_to_have_class(re.compile(r"opacity-50"))
        
        remove_btn_after_reload = page.locator(f'[data-testid="remove-button-{article_url}"]')
        expect(remove_btn_after_reload).to_be_visible()
        
        print("Test Passed!")
        browser.close()

if __name__ == "__main__":
    run()