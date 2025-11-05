"""
Test for article removal bug: Removed articles should persist their 'removed' state
after scraping the same date again.

Bug description:
1. User scrapes a date (e.g., 2025-11-04)
2. User removes one article (e.g., the top one)
3. User refreshes the page OR scrapes the same date again
4. EXPECTED: Article still has "removed" CSS class
5. ACTUAL BUG: Article shows up regularly without "removed" class

This test verifies:
- Article gets "removed" class after clicking Remove button
- Article retains "removed" class after scraping the same date again
- localStorage correctly preserves the removed state
"""

from playwright.sync_api import sync_playwright, expect
import json


def test_article_removal_persists_after_rescrape():
    """
    Test that removed articles maintain their 'removed' CSS class
    after scraping the same date again.
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Navigate to app
        print("1. Loading application...")
        page.goto("http://localhost:5001/", wait_until="domcontentloaded")

        # Clear localStorage to start fresh
        print("\n2. Clearing localStorage...")
        page.evaluate("() => localStorage.clear()")
        storage_length = page.evaluate("() => localStorage.length")
        print(f"   ✓ localStorage cleared: {storage_length} items")

        # ===================================================================
        # STEP 1: Initial scrape for 2025-11-04
        # ===================================================================

        print("\n3. Scraping newsletters for 2025-11-04...")

        # Wait for form to be ready
        page.wait_for_selector("#scrapeForm", timeout=10000)

        # Fill in the date (pick 2025-11-04 as mentioned in bug description)
        test_date = "2024-11-04"
        page.fill("#start_date", test_date)
        page.fill("#end_date", test_date)

        # Click scrape button
        page.click("#scrapeBtn")
        print(f"   ✓ Scrape button clicked for date: {test_date}")

        # Wait for scraping to complete (button text changes back)
        page.wait_for_selector("button:has-text('Scrape Newsletters')", timeout=60000)
        print("   ✓ Initial scraping completed")

        # ===================================================================
        # STEP 2: Verify results appeared
        # ===================================================================

        print("\n4. Verifying results appeared...")

        # Wait for results container
        page.wait_for_selector(".results-container", timeout=10000)

        # Count articles
        articles = page.locator(".article-card")
        article_count = articles.count()
        print(f"   ✓ Found {article_count} articles")

        # Assert at least one article exists
        assert article_count > 0, "No articles found after initial scrape!"

        # Get the first article (as mentioned: "choose the top one")
        first_article = articles.first

        # Get article URL for tracking
        article_url = first_article.locator(".article-link").get_attribute("data-url")
        article_title = first_article.locator(".article-link").text_content()
        print(f"   ✓ First article URL: {article_url}")
        print(f"   ✓ First article title: {article_title[:50]}...")

        # Verify article does NOT have 'removed' class initially
        initial_classes = first_article.get_attribute("class")
        print(f"   ✓ Initial classes: {initial_classes}")
        assert "removed" not in initial_classes, "Article should not be removed initially!"

        # ===================================================================
        # STEP 3: Remove the article
        # ===================================================================

        print("\n5. Removing the first article...")

        # Get baseline styles BEFORE removal
        styles_before = first_article.evaluate("""
            (element) => {
                const computed = window.getComputedStyle(element)
                return {
                    opacity: computed.opacity,
                    borderStyle: computed.borderStyle,
                    backgroundColor: computed.backgroundColor
                }
            }
        """)
        print(f"   ✓ Styles before removal: {styles_before}")

        # Click Remove button
        remove_button = first_article.locator(".remove-article-btn")
        remove_button.click()
        print("   ✓ Remove button clicked")

        # Wait for state change to propagate
        page.wait_for_timeout(1000)

        # ===================================================================
        # STEP 4: Verify 'removed' class is present
        # ===================================================================

        print("\n6. Verifying article has 'removed' class after removal...")

        # Get classes after removal
        classes_after_removal = first_article.get_attribute("class")
        print(f"   ✓ Classes after removal: {classes_after_removal}")

        # ASSERT: Article MUST have 'removed' class
        assert "removed" in classes_after_removal, \
            f"Article should have 'removed' class! Got: {classes_after_removal}"

        # Get styles after removal
        styles_after_removal = first_article.evaluate("""
            (element) => {
                const computed = window.getComputedStyle(element)
                return {
                    opacity: computed.opacity,
                    borderStyle: computed.borderStyle,
                    backgroundColor: computed.backgroundColor
                }
            }
        """)
        print(f"   ✓ Styles after removal: {styles_after_removal}")

        # Verify styles changed
        assert styles_after_removal['opacity'] != styles_before['opacity'], \
            "Opacity should change after removal"
        assert "dashed" in styles_after_removal['borderStyle'], \
            "Border should be dashed after removal"

        # Verify button text changed to "Restore"
        button_text = remove_button.text_content()
        print(f"   ✓ Remove button text: '{button_text}'")
        assert button_text == "Restore", f"Button should say 'Restore', got '{button_text}'"

        # ===================================================================
        # STEP 5: Verify localStorage has removed=true
        # ===================================================================

        print("\n7. Verifying localStorage has removed=true...")

        # Check localStorage for the specific date
        storage_key = f"newsletters:scrapes:{test_date}"
        cached_data = page.evaluate(f"""
            (key) => {{
                const raw = localStorage.getItem(key)
                return raw ? JSON.parse(raw) : null
            }}
        """, storage_key)

        print(f"   ✓ localStorage key: {storage_key}")

        if cached_data:
            # Find our article in the cached data
            removed_article = None
            for article in cached_data.get('articles', []):
                if article.get('url') == article_url or article_url.endswith(article.get('url', '')):
                    removed_article = article
                    break

            assert removed_article is not None, "Could not find article in localStorage!"
            print(f"   ✓ Found article in localStorage: {removed_article.get('title', '')[:30]}...")

            # ASSERT: Article must have removed=true in localStorage
            assert removed_article.get('removed') == True, \
                f"Article should have removed=true in localStorage! Got: {removed_article.get('removed')}"
            print("   ✓ Article has removed=true in localStorage")
        else:
            raise AssertionError(f"No cached data found for {test_date}!")

        # ===================================================================
        # STEP 6: Scrape the SAME DATE again
        # ===================================================================

        print(f"\n8. Scraping the SAME DATE again ({test_date})...")

        # Click scrape button again with the same date
        page.click("#scrapeBtn")
        print(f"   ✓ Scrape button clicked again for date: {test_date}")

        # Wait for scraping to complete
        page.wait_for_selector("button:has-text('Scrape Newsletters')", timeout=60000)
        print("   ✓ Re-scraping completed")

        # Small wait for UI to update
        page.wait_for_timeout(1000)

        # ===================================================================
        # STEP 7: THE BUG CHECK - Verify 'removed' class STILL persists
        # ===================================================================

        print("\n9. 🔍 BUG CHECK: Verifying 'removed' class STILL persists after re-scrape...")

        # Re-locate the first article (DOM might have been re-rendered)
        first_article_after_rescrape = articles.first

        # Get classes after re-scraping
        classes_after_rescrape = first_article_after_rescrape.get_attribute("class")
        print(f"   ✓ Classes after re-scrape: {classes_after_rescrape}")

        # THIS IS THE KEY ASSERTION - THE BUG FIX SHOULD MAKE THIS PASS
        assert "removed" in classes_after_rescrape, \
            f"""
            🐛 BUG DETECTED! Article lost 'removed' class after re-scraping!
            Expected: 'removed' in classes
            Got: {classes_after_rescrape}

            This means the removed state was NOT preserved during re-scraping.
            Possible causes:
            1. mergeWithCache() not preserving removed state
            2. buildDailyPayloadsFromScrape() overwriting removed state
            3. Backend returning excluded articles in response
            """

        print("   ✓ SUCCESS: Article STILL has 'removed' class after re-scrape!")

        # Verify button still says "Restore"
        button_text_after_rescrape = first_article_after_rescrape.locator(".remove-article-btn").text_content()
        assert button_text_after_rescrape == "Restore", \
            f"Button should still say 'Restore', got '{button_text_after_rescrape}'"
        print(f"   ✓ Button still says: '{button_text_after_rescrape}'")

        # Verify styles are still "removed" styles
        styles_after_rescrape = first_article_after_rescrape.evaluate("""
            (element) => {
                const computed = window.getComputedStyle(element)
                return {
                    opacity: computed.opacity,
                    borderStyle: computed.borderStyle
                }
            }
        """)
        print(f"   ✓ Styles after re-scrape: {styles_after_rescrape}")
        assert "dashed" in styles_after_rescrape['borderStyle'], \
            "Border should still be dashed after re-scrape"

        # ===================================================================
        # STEP 8: Verify localStorage STILL has removed=true
        # ===================================================================

        print("\n10. Verifying localStorage STILL has removed=true after re-scrape...")

        cached_data_after_rescrape = page.evaluate(f"""
            (key) => {{
                const raw = localStorage.getItem(key)
                return raw ? JSON.parse(raw) : null
            }}
        """, storage_key)

        if cached_data_after_rescrape:
            # Find our article again
            removed_article_after_rescrape = None
            for article in cached_data_after_rescrape.get('articles', []):
                if article.get('url') == article_url or article_url.endswith(article.get('url', '')):
                    removed_article_after_rescrape = article
                    break

            assert removed_article_after_rescrape is not None, \
                "Could not find article in localStorage after re-scrape!"

            # ASSERT: Article must STILL have removed=true
            assert removed_article_after_rescrape.get('removed') == True, \
                f"""
                🐛 BUG DETECTED! Article lost removed=true in localStorage after re-scrape!
                Got: {removed_article_after_rescrape.get('removed')}
                """
            print("   ✓ Article STILL has removed=true in localStorage")
        else:
            raise AssertionError(f"No cached data found for {test_date} after re-scrape!")

        # ===================================================================
        # OPTIONAL: Take screenshot for debugging
        # ===================================================================

        print("\n11. Taking screenshot for debugging...")
        page.screenshot(path="/tmp/article-removal-after-rescrape.png")
        print("   ✓ Screenshot saved to /tmp/article-removal-after-rescrape.png")

        # Close browser
        browser.close()

        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("   Article removal state persists correctly after re-scraping.")
        print("="*70)


if __name__ == "__main__":
    test_article_removal_persists_after_rescrape()
