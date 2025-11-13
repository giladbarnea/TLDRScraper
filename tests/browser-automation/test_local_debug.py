"""
Deep debugging test for Phase 5 - why aren't articles rendering?
"""

from playwright.sync_api import sync_playwright


def test_local_debug():
    """Debug the article rendering issue"""

    url = "http://localhost:3000/"

    with sync_playwright() as p:
        print("="*80)
        print("PHASE 5 DEBUG TEST - Article Rendering")
        print("="*80)

        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        try:
            print("\n1. Loading page...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            print("   ✓ Page loaded")

            print("\n2. Clicking scrape...")
            page.click("#scrapeBtn")
            page.wait_for_timeout(2000)

            print("\n3. Waiting for completion...")
            page.wait_for_selector(
                ".article-card, button:has-text('Scrape Newsletters')",
                timeout=90000
            )
            print("   ✓ Scraping completed")

            print("\n4. DEEP DOM INSPECTION...")

            # Check what's in the results
            results_html = page.locator("#result").inner_html() if page.locator("#result").count() > 0 else None

            if results_html:
                print(f"   ✓ #result div exists ({len(results_html)} chars)")
                print(f"   First 500 chars:\n{results_html[:500]}")
            else:
                print("   ✗ #result div not found")

            # Check main element
            main_html = page.locator("main#write").inner_html() if page.locator("main#write").count() > 0 else None

            if main_html:
                print(f"\n   ✓ main#write exists ({len(main_html)} chars)")
                print(f"   First 500 chars:\n{main_html[:500]}")
            else:
                print("\n   ✗ main#write not found")

            # Check for date-group divs
            date_groups = page.locator(".date-group").count()
            print(f"\n   ✓ .date-group divs: {date_groups}")

            if date_groups > 0:
                first_date_group = page.locator(".date-group").first.inner_html()
                print(f"   First date-group ({len(first_date_group)} chars):\n{first_date_group[:500]}")

            # Check for article-list divs
            article_lists = page.locator(".article-list").count()
            print(f"\n   ✓ .article-list divs: {article_lists}")

            if article_lists > 0:
                first_list = page.locator(".article-list").first.inner_html()
                print(f"   First article-list ({len(first_list)} chars):\n{first_list[:500]}")

            # Check article-card count again
            article_cards = page.locator(".article-card").count()
            print(f"\n   ✓ .article-card divs: {article_cards}")

            # Execute JS to check React state
            print("\n5. CHECKING REACT STATE...")

            react_debug = page.evaluate("""
                () => {
                    // Try to find React root
                    const root = document.getElementById('root')
                    const resultDiv = document.getElementById('result')
                    const mainDiv = document.getElementById('write')

                    return {
                        root_exists: !!root,
                        root_has_children: root ? root.children.length : 0,
                        result_exists: !!resultDiv,
                        result_has_children: resultDiv ? resultDiv.children.length : 0,
                        main_exists: !!mainDiv,
                        main_has_children: mainDiv ? mainDiv.children.length : 0,
                        article_cards: document.querySelectorAll('.article-card').length,
                        date_groups: document.querySelectorAll('.date-group').length,
                        article_lists: document.querySelectorAll('.article-list').length,
                    }
                }
            """)

            print("   React/DOM State:")
            for key, val in react_debug.items():
                print(f"      {key}: {val}")

            # Check if articles array is in state
            print("\n6. CHECKING RESULTS DATA...")

            has_results_data = page.evaluate("""
                () => {
                    // Try to peek at the results in React state
                    // This is hacky but might give us insight
                    const statsDiv = document.querySelector('.stats')
                    if (statsDiv) {
                        return {
                            stats_text: statsDiv.textContent,
                            found_stats: true
                        }
                    }
                    return {found_stats: false}
                }
            """)

            print(f"   Stats data: {has_results_data}")

            # Check console logs for clues
            print("\n7. CONSOLE LOGS...")
            if console_logs:
                print(f"   Total logs: {len(console_logs)}")
                for log in console_logs[:20]:
                    print(f"      {log}")
            else:
                print("   No console logs captured")

            # Look for specific errors
            error_logs = [log for log in console_logs if 'error' in log.lower() or 'warning' in log.lower() or 'failed' in log.lower()]
            if error_logs:
                print(f"\n   🔴 Errors/warnings ({len(error_logs)}):")
                for log in error_logs:
                    print(f"      {log}")

            # Check if ArticleList component is rendering
            print("\n8. CHECKING COMPONENT STRUCTURE...")

            component_check = page.evaluate("""
                () => {
                    const dateGroups = document.querySelectorAll('.date-group')
                    const results = []

                    dateGroups.forEach((group, i) => {
                        const dateHeader = group.querySelector('.date-header-container')
                        const issueSections = group.querySelectorAll('.issue-section')
                        const articleLists = group.querySelectorAll('.article-list')

                        results.push({
                            index: i,
                            has_date_header: !!dateHeader,
                            date_text: dateHeader ? dateHeader.textContent.trim() : null,
                            issue_sections: issueSections.length,
                            article_lists: articleLists.length,
                        })
                    })

                    return results
                }
            """)

            if component_check:
                print(f"   Found {len(component_check)} date group(s):")
                for comp in component_check:
                    print(f"      Date group {comp['index']}:")
                    print(f"         Date: {comp['date_text']}")
                    print(f"         Issue sections: {comp['issue_sections']}")
                    print(f"         Article lists: {comp['article_lists']}")

            # Final screenshot with full page
            print("\n9. Saving debug screenshot...")
            page.screenshot(path="/tmp/local_debug_full.png", full_page=True)
            print("   ✓ Saved: /tmp/local_debug_full.png")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

        finally:
            browser.close()

        print("\n" + "="*80)
        print("✓ DEBUG TEST COMPLETED")
        print("="*80)


if __name__ == "__main__":
    test_local_debug()
