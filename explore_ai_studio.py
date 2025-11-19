#!/usr/bin/env python3
"""Explore AI Studio Drive URL with Playwright"""
import time
from playwright.sync_api import sync_playwright

URL = "https://aistudio.google.com/apps/drive/1jHMSnfyJjS21tQoY04MQbuSlRGE6b2ir"

def main():
    launch_options = {
        'headless': True,
        'args': [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
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

        # Set up event listeners
        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))
        page.on("requestfailed", lambda req: print(f"[REQUEST FAILED] {req.url} - {req.failure}"))

        print(f"Navigating to {URL}...")
        try:
            response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            print(f"Response status: {response.status if response else 'No response'}")
            print(f"Final URL after redirects: {page.url}")
        except Exception as e:
            print(f"Navigation error: {e}")
            print(f"Current URL: {page.url}")

        # Wait for body to be visible
        try:
            page.wait_for_selector('body', state="visible", timeout=10000)
        except Exception as e:
            print(f"Body wait error: {e}")

        # Wait for React hydration
        time.sleep(3)

        # Take screenshot
        screenshot_path = "/home/user/TLDRScraper/ai_studio_screenshot.png"
        try:
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved to {screenshot_path}")
        except Exception as e:
            print(f"Screenshot error: {e}")

        # Get page title and URL
        print(f"Page title: {page.title()}")
        print(f"Current URL: {page.url}")

        # Get page content structure
        print("\n=== Page Structure ===")
        body_html = page.locator('body').inner_html()
        print(f"Body HTML length: {len(body_html)} chars")

        # Check for common elements
        headings = page.locator('h1, h2, h3').all()
        print(f"Found {len(headings)} headings")
        for i, h in enumerate(headings[:5]):
            print(f"  {i+1}. {h.text_content()}")

        # Check for interactive elements
        buttons = page.locator('button').all()
        links = page.locator('a').all()
        inputs = page.locator('input').all()
        print(f"\nInteractive elements: {len(buttons)} buttons, {len(links)} links, {len(inputs)} inputs")

        # Get any visible text content
        print("\n=== Visible Text (first 500 chars) ===")
        text_content = page.locator('body').text_content()
        print(text_content[:500] if text_content else "No text content")

        browser.close()
        print("\nDone!")

if __name__ == "__main__":
    main()
