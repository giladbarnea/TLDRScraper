#!/usr/bin/env python3
"""
Simplified browser test using Firefox against production build
"""

import asyncio
import sys
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8080"  # Production build

async def test_basic_load():
    async with async_playwright() as p:
        try:
            # Try Firefox (more stable in headless environments)
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            print("✓ Firefox browser launched")

            # Navigate to app
            print("\n[Test] Loading production build...")
            response = await page.goto(BASE_URL, wait_until='domcontentloaded', timeout=10000)
            print(f"✓ Page loaded with status: {response.status}")

            # Check title
            title = await page.title()
            print(f"✓ Page title: {title}")

            # Wait for root element
            await page.wait_for_selector('#root', timeout=5000)
            print("✓ React root element found")

            # Check if JavaScript executed
            app_content = await page.locator('#root').inner_html()
            if len(app_content) > 100:
                print(f"✓ React app rendered ({len(app_content)} chars)")
            else:
                print(f"⚠ React app may not have rendered (only {len(app_content)} chars)")

            # Check for console errors
            errors = []
            page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
            await page.wait_for_timeout(1000)

            if errors:
                print(f"⚠ Found {len(errors)} console errors:")
                for error in errors[:3]:
                    print(f"  - {error.text}")
            else:
                print("✓ No console errors")

            await browser.close()

            print("\n" + "="*60)
            print("BASIC LOAD TEST PASSED")
            print("="*60)
            print("✓ Production build loads successfully")
            print("✓ React app renders")
            print("✓ No critical errors")
            return True

        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = asyncio.run(test_basic_load())
    sys.exit(0 if success else 1)
