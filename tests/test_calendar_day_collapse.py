"""
Test: Calendar Day Collapse Behavior
Verifies that calendar days collapse and dim when all newsletter days are removed.
"""
import requests
from datetime import datetime, timedelta


BASE_URL = "http://localhost:5001"
CLIENT_URL = "http://localhost:3000"


def setup_test_data():
    """Create test data with multiple newsletters and articles"""
    test_date = (datetime.now() + timedelta(days=200)).strftime("%Y-%m-%d")
    
    payload = {
        "date": test_date,
        "cachedAt": datetime.now().isoformat(),
        "articles": [
            {
                "url": "https://example.com/article1",
                "title": "Article 1",
                "issueDate": test_date,
                "category": "Newsletter A",
                "removed": False,
                "tldrHidden": False,
                "read": {"isRead": False, "markedAt": None},
                "tldr": {"status": "unknown", "markdown": ""}
            },
            {
                "url": "https://example.com/article2",
                "title": "Article 2",
                "issueDate": test_date,
                "category": "Newsletter A",
                "removed": False,
                "tldrHidden": False,
                "read": {"isRead": False, "markedAt": None},
                "tldr": {"status": "unknown", "markdown": ""}
            },
            {
                "url": "https://example.com/article3",
                "title": "Article 3",
                "issueDate": test_date,
                "category": "Newsletter B",
                "removed": False,
                "tldrHidden": False,
                "read": {"isRead": False, "markedAt": None},
                "tldr": {"status": "unknown", "markdown": ""}
            }
        ],
        "issues": [
            {"date": test_date, "category": "Newsletter A"},
            {"date": test_date, "category": "Newsletter B"}
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/storage/daily/{test_date}",
        json={"payload": payload}
    )
    assert response.status_code == 200
    print(f"✓ Created test data for {test_date}")
    return test_date, payload


def test_calendar_day_not_collapsed_initially():
    """Test 1: Calendar day should not be collapsed when newsletters have unremoved articles"""
    print("\n=== Test 1: Calendar Day Not Collapsed Initially ===")
    
    from playwright.sync_api import sync_playwright
    
    test_date, _ = setup_test_data()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ]
        )
        page = browser.new_page()
        
        page.goto(f"{CLIENT_URL}?date={test_date}")
        page.wait_for_selector(f'[data-all-removed]', timeout=10000)
        
        calendar_day_removed = page.evaluate(f"""
            document.querySelector('section[data-all-removed]').getAttribute('data-all-removed')
        """)
        
        assert calendar_day_removed == "false", f"Expected false, got {calendar_day_removed}"
        print("✓ Calendar day data-all-removed = false")
        
        newsletter_days = page.evaluate("""
            Array.from(document.querySelectorAll('[id^="newsletter-"]')).map(el => 
                el.parentElement.getAttribute('data-all-removed')
            )
        """)
        
        assert all(removed == "false" for removed in newsletter_days), "All newsletter days should have data-all-removed=false"
        print(f"✓ All {len(newsletter_days)} newsletter days have data-all-removed = false")
        
        browser.close()


def test_calendar_day_partially_collapsed():
    """Test 2: Calendar day should not collapse when only some newsletters are removed"""
    print("\n=== Test 2: Calendar Day Partially Collapsed ===")
    
    from playwright.sync_api import sync_playwright
    
    test_date, payload = setup_test_data()
    
    payload["articles"][0]["removed"] = True
    payload["articles"][1]["removed"] = True
    
    response = requests.post(
        f"{BASE_URL}/api/storage/daily/{test_date}",
        json={"payload": payload}
    )
    assert response.status_code == 200
    print("✓ Removed all articles from Newsletter A")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ]
        )
        page = browser.new_page()
        
        page.goto(f"{CLIENT_URL}?date={test_date}")
        page.wait_for_selector(f'section[data-all-removed]', timeout=10000)
        
        calendar_day_removed = page.evaluate("""
            document.querySelector('section[data-all-removed]').getAttribute('data-all-removed')
        """)
        
        assert calendar_day_removed == "false", f"Calendar day should not be collapsed when only one newsletter is removed. Got {calendar_day_removed}"
        print("✓ Calendar day data-all-removed = false (partial removal)")
        
        newsletter_a_removed = page.evaluate("""
            document.querySelector('[id*="Newsletter-A"]')?.parentElement.getAttribute('data-all-removed')
        """)
        
        assert newsletter_a_removed == "true", f"Newsletter A should be collapsed. Got {newsletter_a_removed}"
        print("✓ Newsletter A data-all-removed = true")
        
        browser.close()


def test_calendar_day_fully_collapsed():
    """Test 3: Calendar day should collapse when all newsletters are removed"""
    print("\n=== Test 3: Calendar Day Fully Collapsed ===")
    
    from playwright.sync_api import sync_playwright
    
    test_date, payload = setup_test_data()
    
    for article in payload["articles"]:
        article["removed"] = True
    
    response = requests.post(
        f"{BASE_URL}/api/storage/daily/{test_date}",
        json={"payload": payload}
    )
    assert response.status_code == 200
    print("✓ Removed all articles from all newsletters")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ]
        )
        page = browser.new_page()
        
        page.goto(f"{CLIENT_URL}?date={test_date}")
        page.wait_for_selector(f'section[data-all-removed]', timeout=10000)
        
        calendar_day_removed = page.evaluate("""
            document.querySelector('section[data-all-removed]').getAttribute('data-all-removed')
        """)
        
        assert calendar_day_removed == "true", f"Calendar day should be collapsed when all newsletters are removed. Got {calendar_day_removed}"
        print("✓ Calendar day data-all-removed = true")
        
        calendar_day_opacity = page.evaluate("""
            window.getComputedStyle(document.querySelector('section[data-all-removed] > div > div')).opacity
        """)
        
        assert float(calendar_day_opacity) < 1.0, f"Calendar day should have reduced opacity. Got {calendar_day_opacity}"
        print(f"✓ Calendar day has dim styling (opacity = {calendar_day_opacity})")
        
        newsletter_days_removed = page.evaluate("""
            Array.from(document.querySelectorAll('[id^="newsletter-"]')).map(el => 
                el.parentElement.getAttribute('data-all-removed')
            )
        """)
        
        assert all(removed == "true" for removed in newsletter_days_removed), "All newsletter days should have data-all-removed=true"
        print(f"✓ All {len(newsletter_days_removed)} newsletter days have data-all-removed = true")
        
        browser.close()


def run_all_tests():
    """Run all calendar day collapse tests"""
    print("\n" + "="*60)
    print("CALENDAR DAY COLLAPSE TESTS")
    print("="*60)
    
    try:
        test_calendar_day_not_collapsed_initially()
        test_calendar_day_partially_collapsed()
        test_calendar_day_fully_collapsed()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
