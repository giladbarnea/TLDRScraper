#!/usr/bin/env python3
"""
Simple demo showing Playwright's localStorage capabilities
Run this to see it in action!
"""

from playwright.sync_api import sync_playwright
import json


def demo_localstorage():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load a simple page
        page.set_content("""
            <html>
                <head><title>localStorage Test</title></head>
                <body>
                    <h1>Testing localStorage</h1>
                    <div id="output"></div>
                    <script>
                        function updateOutput() {
                            const output = document.getElementById('output')
                            output.innerHTML = '<pre>' + JSON.stringify(localStorage, null, 2) + '</pre>'
                        }
                        updateOutput()
                    </script>
                </body>
            </html>
        """)

        print("=" * 60)
        print("PLAYWRIGHT LOCALSTORAGE DEMO")
        print("=" * 60)

        # 1. Clear localStorage
        print("\n1. Clearing localStorage...")
        page.evaluate("() => localStorage.clear()")
        length = page.evaluate("() => localStorage.length")
        print(f"   ✓ localStorage cleared: {length} items")

        # 2. Set some values
        print("\n2. Setting values...")
        page.evaluate("""
            () => {
                localStorage.setItem('user', 'Alice')
                localStorage.setItem('cache-enabled', 'true')
                localStorage.setItem('theme', 'dark')
            }
        """)
        length = page.evaluate("() => localStorage.length")
        print(f"   ✓ Set 3 items, localStorage now has {length} items")

        # 3. Get individual values
        print("\n3. Getting individual values...")
        user = page.evaluate("() => localStorage.getItem('user')")
        theme = page.evaluate("() => localStorage.getItem('theme')")
        print(f"   ✓ user = {user}")
        print(f"   ✓ theme = {theme}")

        # 4. Set complex JSON data (like your newsletter cache!)
        print("\n4. Setting complex JSON data (like newsletter cache)...")
        newsletter_data = {
            "date": "2024-11-01",
            "newsletters": [
                {
                    "title": "Test Newsletter 1",
                    "url": "https://example.com/1",
                    "removed": False,
                    "read": False
                },
                {
                    "title": "Test Newsletter 2",
                    "url": "https://example.com/2",
                    "removed": True,
                    "read": True
                }
            ],
            "stats": {
                "total": 2,
                "removed": 1
            }
        }

        page.evaluate("""
            (data) => {
                localStorage.setItem('newsletters:scrapes:2024-11-01', JSON.stringify(data))
            }
        """, newsletter_data)
        print("   ✓ Stored complex newsletter data")

        # 5. Retrieve and parse JSON
        print("\n5. Retrieving complex JSON data...")
        retrieved = page.evaluate("""
            () => {
                const raw = localStorage.getItem('newsletters:scrapes:2024-11-01')
                return JSON.parse(raw)
            }
        """)
        print(f"   ✓ Retrieved data:")
        print(f"     - Date: {retrieved['date']}")
        print(f"     - Newsletters: {len(retrieved['newsletters'])}")
        print(f"     - First title: {retrieved['newsletters'][0]['title']}")
        print(f"     - Stats: {retrieved['stats']}")

        # 6. Get all keys
        print("\n6. Getting all localStorage keys...")
        all_keys = page.evaluate("""
            () => {
                const keys = []
                for (let i = 0; i < localStorage.length; i++) {
                    keys.push(localStorage.key(i))
                }
                return keys
            }
        """)
        print(f"   ✓ All keys: {all_keys}")

        # 7. Filter keys by prefix (like your app does!)
        print("\n7. Filtering keys by prefix...")
        newsletter_keys = page.evaluate("""
            () => {
                const keys = []
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i)
                    if (key.startsWith('newsletters:')) {
                        keys.push(key)
                    }
                }
                return keys
            }
        """)
        print(f"   ✓ Newsletter keys: {newsletter_keys}")

        # 8. Modify nested data (mark article as removed)
        print("\n8. Modifying nested data (mark article as removed)...")
        page.evaluate("""
            () => {
                const raw = localStorage.getItem('newsletters:scrapes:2024-11-01')
                const data = JSON.parse(raw)

                // Find first newsletter and mark as removed
                data.newsletters[0].removed = true
                data.stats.removed = 2

                localStorage.setItem('newsletters:scrapes:2024-11-01', JSON.stringify(data))
            }
        """)

        # Verify the change
        updated = page.evaluate("""
            () => {
                const raw = localStorage.getItem('newsletters:scrapes:2024-11-01')
                const data = JSON.parse(raw)
                return {
                    first_removed: data.newsletters[0].removed,
                    total_removed: data.stats.removed
                }
            }
        """)
        print(f"   ✓ First article removed: {updated['first_removed']}")
        print(f"   ✓ Total removed: {updated['total_removed']}")

        # 9. Dump entire localStorage
        print("\n9. Dumping entire localStorage...")
        full_dump = page.evaluate("""
            () => {
                const dump = {}
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i)
                    dump[key] = localStorage.getItem(key)
                }
                return dump
            }
        """)
        print("   ✓ Full localStorage dump:")
        for key, value in full_dump.items():
            preview = value[:60] + "..." if len(value) > 60 else value
            print(f"     {key}: {preview}")

        # 10. Remove specific item
        print("\n10. Removing specific item...")
        page.evaluate("() => localStorage.removeItem('theme')")
        has_theme = page.evaluate("() => localStorage.getItem('theme') !== null")
        print(f"   ✓ Theme exists after removal: {has_theme}")

        browser.close()

        print("\n" + "=" * 60)
        print("✅ PLAYWRIGHT HAS FULL LOCALSTORAGE ACCESS!")
        print("You can do ANYTHING with localStorage in your tests!")
        print("=" * 60)


if __name__ == "__main__":
    demo_localstorage()
