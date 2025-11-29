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
        page = context.new_page()

        # Enable console logging
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"BROWSER ERROR: {exc}"))

        print("Navigating to app...")
        page.goto("http://localhost:3000")
        page.wait_for_load_state("networkidle")

        # Fill dates
        print("Filling dates...")
        page.fill('#start_date', today)
        page.fill('#end_date', today)
        
        print("Clicking Update Feed...")
        page.click('button:has-text("Update Feed")', force=True)

        # Wait for results
        print("Waiting for results...")
        page.wait_for_selector('div[data-testid^="article-card-"]', timeout=120000)
        
        # Get first article
        article_card = page.locator('div[data-testid^="article-card-"]').first
        article_url = article_card.get_attribute("data-testid").replace("article-card-", "")
        print(f"Testing article: {article_url}")
        
        # Locate TLDR button
        # The button has text "TLDR" initially
        tldr_btn = article_card.locator('button:has-text("TLDR")')
        
        if not tldr_btn.is_visible():
            print("TLDR button not found or already expanded?")
            # Check if it says "Close"
            close_btn = article_card.locator('button:has-text("Close")')
            if close_btn.is_visible():
                print("It says Close, so it's already expanded.")
                tldr_btn = close_btn
            else:
                 print("Neither TLDR nor Close button found.")
                 # Dump html
                 print(article_card.inner_html())
                 raise Exception("TLDR button missing")

        print("Clicking TLDR button...")
        tldr_btn.click(force=True)
        
        # Wait for loading to finish and content to appear
        # The button text should change to "Close"
        print("Waiting for Close button...")
        close_btn = article_card.locator('button:has-text("Close")')
        expect(close_btn).to_be_visible(timeout=60000)
        
        print("Debug: Close button found. Checking properties...")
        # Check disabled state
        is_disabled = close_btn.is_disabled()
        print(f"Debug: Button disabled: {is_disabled}")
        
        content_div = article_card.locator('.prose')
        
        print("Clicking Close button via JS...")
        # Try JS click to ensure event firing
        close_btn.evaluate("el => el.click()")
        
        # Wait a bit for transition
        time.sleep(1)
        
        # Check classes of the container
        # The container is the parent of .prose's parent (animate-fade-in)
        # Structure: 
        # <div class="transition-all ..."> 
        #   <div class="animate-fade-in">
        #     <div class="prose ...">
        
        container = article_card.locator('.prose').locator('xpath=../..')
        print(f"Debug: Container classes: {container.get_attribute('class')}")
        
        print("Debug: Article Card HTML:")
        print(article_card.inner_html())

        print("Verifying content is hidden...")
        expect(content_div).not_to_be_visible()
        
        print("Test Passed!")
        browser.close()

if __name__ == "__main__":
    run()
