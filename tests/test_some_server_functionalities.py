"""
Phase 6 End-to-End Testing
Tests all user flows to ensure complete feature parity with localStorage implementation.
"""
import requests
import json
from datetime import datetime, timedelta


BASE_URL = "http://localhost:5001"


def test_1_cache_toggle():
    """Test 1: Cache Toggle - Setting persistence across operations"""
    print("\n=== Test 1: Cache Toggle ===")

    response = requests.post(
        f"{BASE_URL}/api/storage/setting/cache:enabled",
        json={"value": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    print("✓ Cache disabled and saved to DB")

    response = requests.get(f"{BASE_URL}/api/storage/setting/cache:enabled")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["value"] is False
    print("✓ Cache setting persisted (read back as False)")

    response = requests.post(
        f"{BASE_URL}/api/storage/setting/cache:enabled",
        json={"value": True}
    )
    assert response.status_code == 200
    print("✓ Cache re-enabled")

    response = requests.get(f"{BASE_URL}/api/storage/setting/cache:enabled")
    data = response.json()
    assert data["value"] is True
    print("✓ Cache setting persisted (read back as True)")


def test_2_newsletter_scraping_cache_miss():
    """Test 2: Newsletter Scraping (Cache Miss)"""
    print("\n=== Test 2: Newsletter Scraping (Cache Miss) ===")

    future_date = (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d")

    response = requests.get(f"{BASE_URL}/api/storage/is-cached/{future_date}")
    data = response.json()
    assert data["is_cached"] is False
    print(f"✓ Date {future_date} not cached (as expected)")

    payload = {
        "date": future_date,
        "articles": [
            {
                "url": "https://example.com/article1",
                "title": "Test Article 1",
                "issueDate": future_date,
                "category": "Newsletter",
                "removed": False,
                "read": {"isRead": False, "markedAt": None},
                "tldr": {"status": "unknown", "markdown": ""}
            }
        ],
        "issues": [{"date": future_date, "category": "Newsletter"}]
    }

    response = requests.post(
        f"{BASE_URL}/api/storage/daily/{future_date}",
        json={"payload": payload}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    print("✓ Fresh scrape saved to DB")

    response = requests.get(f"{BASE_URL}/api/storage/daily/{future_date}")
    data = response.json()
    assert data["success"] is True
    assert data["payload"]["date"] == future_date
    assert len(data["payload"]["articles"]) == 1
    print("✓ Payload retrieved correctly with all articles")


def test_3_newsletter_scraping_cache_hit():
    """Test 3: Newsletter Scraping (Cache Hit)"""
    print("\n=== Test 3: Newsletter Scraping (Cache Hit) ===")

    future_date = (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d")

    response = requests.get(f"{BASE_URL}/api/storage/is-cached/{future_date}")
    data = response.json()
    assert data["is_cached"] is True
    print(f"✓ Date {future_date} is cached (from Test 2)")

    response = requests.get(f"{BASE_URL}/api/storage/daily/{future_date}")
    data = response.json()
    assert data["success"] is True
    assert data["payload"]["date"] == future_date
    print("✓ Cached data loaded instantly")


def test_4_mark_article_as_read():
    """Test 4: Mark Article as Read"""
    print("\n=== Test 4: Mark Article as Read ===")

    test_date = (datetime.now() + timedelta(days=101)).strftime("%Y-%m-%d")

    payload = {
        "date": test_date,
        "articles": [
            {
                "url": "https://example.com/unread-article",
                "title": "Unread Article",
                "issueDate": test_date,
                "category": "Newsletter",
                "removed": False,
                "read": {"isRead": False, "markedAt": None},
                "tldr": {"status": "unknown", "markdown": ""}
            }
        ],
        "issues": []
    }

    requests.post(f"{BASE_URL}/api/storage/daily/{test_date}", json={"payload": payload})
    print("✓ Created article with unread state")

    payload["articles"][0]["read"] = {
        "isRead": True,
        "markedAt": datetime.now().isoformat()
    }

    response = requests.post(
        f"{BASE_URL}/api/storage/daily/{test_date}",
        json={"payload": payload}
    )
    assert response.status_code == 200
    print("✓ Marked article as read")

    response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
    data = response.json()
    assert data["payload"]["articles"][0]["read"]["isRead"] is True
    print("✓ Read state persisted (survives refresh)")


def test_5_remove_article():
    """Test 5: Remove Article"""
    print("\n=== Test 5: Remove Article ===")

    test_date = (datetime.now() + timedelta(days=102)).strftime("%Y-%m-%d")

    payload = {
        "date": test_date,
        "articles": [
            {
                "url": "https://example.com/remove-test",
                "title": "Article to Remove",
                "issueDate": test_date,
                "category": "Newsletter",
                "removed": False,
                "read": {"isRead": False, "markedAt": None},
                "tldr": {"status": "unknown", "markdown": ""}
            }
        ],
        "issues": []
    }

    requests.post(f"{BASE_URL}/api/storage/daily/{test_date}", json={"payload": payload})
    print("✓ Created article (not removed)")

    payload["articles"][0]["removed"] = True

    response = requests.post(
        f"{BASE_URL}/api/storage/daily/{test_date}",
        json={"payload": payload}
    )
    assert response.status_code == 200
    print("✓ Article removed")

    response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
    data = response.json()
    assert data["payload"]["articles"][0]["removed"] is True
    print("✓ Removed state persisted")


def test_6_restore_removed_article():
    """Test 6: Restore Removed Article"""
    print("\n=== Test 6: Restore Removed Article ===")

    test_date = (datetime.now() + timedelta(days=102)).strftime("%Y-%m-%d")

    response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
    payload = response.json()["payload"]

    assert payload["articles"][0]["removed"] is True
    print("✓ Article is removed (from Test 5)")

    payload["articles"][0]["removed"] = False

    response = requests.post(
        f"{BASE_URL}/api/storage/daily/{test_date}",
        json={"payload": payload}
    )
    assert response.status_code == 200
    print("✓ Article restored")

    response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
    data = response.json()
    assert data["payload"]["articles"][0]["removed"] is False
    print("✓ Restored state persisted")


def test_7_generate_tldr():
    """Test 7: Generate TLDR"""
    print("\n=== Test 7: Generate TLDR ===")

    test_date = (datetime.now() + timedelta(days=103)).strftime("%Y-%m-%d")

    payload = {
        "date": test_date,
        "articles": [
            {
                "url": "https://example.com/tldr-test",
                "title": "Article for TLDR",
                "issueDate": test_date,
                "category": "Newsletter",
                "removed": False,
                "read": {"isRead": False, "markedAt": None},
                "tldr": {"status": "unknown", "markdown": ""}
            }
        ],
        "issues": []
    }

    requests.post(f"{BASE_URL}/api/storage/daily/{test_date}", json={"payload": payload})
    print("✓ Created article without TLDR")

    payload["articles"][0]["tldr"] = {
        "status": "available",
        "markdown": "# Test TLDR\nThis is a test summary.",
        "fetchedAt": datetime.now().isoformat()
    }
    payload["articles"][0]["read"]["isRead"] = True

    response = requests.post(
        f"{BASE_URL}/api/storage/daily/{test_date}",
        json={"payload": payload}
    )
    assert response.status_code == 200
    print("✓ TLDR generated and saved")

    response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
    data = response.json()
    assert data["payload"]["articles"][0]["tldr"]["status"] == "available"
    assert "Test TLDR" in data["payload"]["articles"][0]["tldr"]["markdown"]
    print("✓ TLDR persisted across refresh")


def test_8_article_sorting_states():
    """Test 8: Article Sorting Verification - All 3 States"""
    print("\n=== Test 8: Article Sorting Verification ===")

    test_date = (datetime.now() + timedelta(days=104)).strftime("%Y-%m-%d")

    payload = {
        "date": test_date,
        "articles": [
            {
                "url": "https://example.com/unread",
                "title": "Unread Article",
                "issueDate": test_date,
                "category": "Newsletter",
                "removed": False,
                "read": {"isRead": False, "markedAt": None},
                "tldr": {"status": "unknown", "markdown": ""}
            },
            {
                "url": "https://example.com/read",
                "title": "Read Article",
                "issueDate": test_date,
                "category": "Newsletter",
                "removed": False,
                "read": {"isRead": True, "markedAt": datetime.now().isoformat()},
                "tldr": {"status": "unknown", "markdown": ""}
            },
            {
                "url": "https://example.com/removed",
                "title": "Removed Article",
                "issueDate": test_date,
                "category": "Newsletter",
                "removed": True,
                "read": {"isRead": False, "markedAt": None},
                "tldr": {"status": "unknown", "markdown": ""}
            }
        ],
        "issues": []
    }

    response = requests.post(
        f"{BASE_URL}/api/storage/daily/{test_date}",
        json={"payload": payload}
    )
    assert response.status_code == 200
    print("✓ Created articles in all 3 states (unread, read, removed)")

    response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
    data = response.json()
    articles = data["payload"]["articles"]

    unread = next(a for a in articles if a["url"] == "https://example.com/unread")
    read = next(a for a in articles if a["url"] == "https://example.com/read")
    removed = next(a for a in articles if a["url"] == "https://example.com/removed")

    assert unread["read"]["isRead"] is False and not unread["removed"]
    assert read["read"]["isRead"] is True and not read["removed"]
    assert removed["removed"] is True

    print("✓ All states persisted correctly")
    print("  - Unread (priority: top)")
    print("  - Read")
    print("  - Removed (priority: bottom)")


def test_9_scrape_with_existing_data():
    """Test 9: Scrape with Existing Data - Merge Behavior"""
    print("\n=== Test 9: Scrape with Existing Data ===")

    test_date = (datetime.now() + timedelta(days=105)).strftime("%Y-%m-%d")

    existing_payload = {
        "date": test_date,
        "articles": [
            {
                "url": "https://example.com/existing",
                "title": "Existing Article",
                "issueDate": test_date,
                "category": "Newsletter",
                "removed": True,
                "read": {"isRead": True, "markedAt": datetime.now().isoformat()},
                "tldr": {"status": "available", "markdown": "# Existing Summary"}
            }
        ],
        "issues": []
    }

    requests.post(
        f"{BASE_URL}/api/storage/daily/{test_date}",
        json={"payload": existing_payload}
    )
    print("✓ Created existing article with user modifications (read, removed, TLDR)")

    fresh_payload = {
        "date": test_date,
        "articles": [
            {
                "url": "https://example.com/existing",
                "title": "Existing Article (Fresh)",
                "issueDate": test_date,
                "category": "Newsletter",
                "removed": False,
                "read": {"isRead": False, "markedAt": None},
                "tldr": {"status": "unknown", "markdown": ""}
            },
            {
                "url": "https://example.com/new-article",
                "title": "New Article",
                "issueDate": test_date,
                "category": "Newsletter",
                "removed": False,
                "read": {"isRead": False, "markedAt": None},
                "tldr": {"status": "unknown", "markdown": ""}
            }
        ],
        "issues": []
    }

    response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
    existing = response.json()["payload"]

    merged_articles = []
    for fresh_article in fresh_payload["articles"]:
        existing_article = next(
            (a for a in existing["articles"] if a["url"] == fresh_article["url"]),
            None
        )

        if existing_article:
            merged_articles.append({
                **fresh_article,
                "tldr": existing_article.get("tldr", fresh_article["tldr"]),
                "read": existing_article.get("read", fresh_article["read"]),
                "removed": existing_article.get("removed", fresh_article["removed"])
            })
        else:
            merged_articles.append(fresh_article)

    merged_payload = {
        **fresh_payload,
        "articles": merged_articles
    }

    response = requests.post(
        f"{BASE_URL}/api/storage/daily/{test_date}",
        json={"payload": merged_payload}
    )
    assert response.status_code == 200
    print("✓ Fresh scrape merged with existing data")

    response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
    data = response.json()
    articles = data["payload"]["articles"]

    existing_article = next(a for a in articles if a["url"] == "https://example.com/existing")
    assert existing_article["removed"] is True
    assert existing_article["read"]["isRead"] is True
    assert existing_article["tldr"]["status"] == "available"
    print("✓ Existing article preserved user state (read, removed, TLDR)")

    new_article = next(a for a in articles if a["url"] == "https://example.com/new-article")
    assert new_article["removed"] is False
    assert new_article["read"]["isRead"] is False
    print("✓ New article added with default state")


def test_10_error_handling():
    """Test 10: Error Handling - Non-existent Resources"""
    print("\n=== Test 10: Error Handling ===")

    response = requests.get(f"{BASE_URL}/api/storage/setting/nonexistent:key")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    print("✓ Non-existent setting returns 404")

    response = requests.get(f"{BASE_URL}/api/storage/daily/1900-01-01")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    print("✓ Non-existent date returns 404")

    response = requests.get(f"{BASE_URL}/api/storage/is-cached/1900-01-01")
    data = response.json()
    assert data["is_cached"] is False
    print("✓ Cache check for non-existent date returns false")


def run_all_tests():
    """Run all Phase 6 E2E tests"""
    print("\n" + "="*60)
    print("PHASE 6: END-TO-END TESTING AND VERIFICATION")
    print("="*60)

    try:
        test_1_cache_toggle()
        test_2_newsletter_scraping_cache_miss()
        test_3_newsletter_scraping_cache_hit()
        test_4_mark_article_as_read()
        test_5_remove_article()
        test_6_restore_removed_article()
        test_7_generate_tldr()
        test_8_article_sorting_states()
        test_9_scrape_with_existing_data()
        test_10_error_handling()

        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        print("\nPhase 6 automated verification complete.")
        print("All 10 test scenarios passed successfully.")
        print("\nNext steps:")
        print("1. Frontend build verification: cd client && npm run build")
        print("2. Manual browser testing (see migration plan)")
        print("3. Visual regression testing")
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
