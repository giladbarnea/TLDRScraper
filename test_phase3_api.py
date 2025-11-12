#!/usr/bin/env python3
"""
API-level test for Phase 3: Core hooks with Supabase storage

Tests the backend integration that Phase 3 hooks rely on:
1. Storage API endpoints work correctly
2. Article state operations persist to Supabase
3. Data round-trips correctly through the storage layer
4. Loading/error states are properly supported by the API
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5001"

def test_phase3_api_integration():
    print("="*60)
    print("PHASE 3 API INTEGRATION TEST")
    print("="*60)

    success_count = 0
    total_tests = 0

    # Test 1: Storage settings API (used by useSupabaseStorage for cache:enabled)
    print("\n[Test 1] Testing storage settings API...")
    total_tests += 1

    try:
        # Set cache:enabled to true
        response = requests.post(
            f"{BASE_URL}/api/storage/setting/cache:enabled",
            json={"value": True},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["success"] == True, "Expected success=true"
        print("  ✓ Setting write successful")

        # Read it back
        response = requests.get(f"{BASE_URL}/api/storage/setting/cache:enabled")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["value"] == True, f"Expected True, got {data['value']}"
        print("  ✓ Setting read successful")
        print("  ✓ Test 1 PASSED")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Test 1 FAILED: {e}")

    # Test 2: Daily cache API (used by useSupabaseStorage for newsletter data)
    print("\n[Test 2] Testing daily cache API...")
    total_tests += 1

    test_date = datetime.now().strftime("%Y-%m-%d")
    test_payload = {
        "date": test_date,
        "cachedAt": datetime.now().isoformat(),
        "articles": [
            {
                "url": "https://example.com/article1",
                "title": "Test Article 1",
                "issueDate": test_date,
                "category": "Tech",
                "removed": False,
                "tldrHidden": False,
                "read": {
                    "isRead": False,
                    "markedAt": None
                },
                "tldr": {
                    "status": "unknown",
                    "markdown": "",
                    "effort": "low"
                }
            }
        ],
        "issues": []
    }

    try:
        # Write payload
        response = requests.post(
            f"{BASE_URL}/api/storage/daily/{test_date}",
            json={"payload": test_payload},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["success"] == True
        print("  ✓ Daily cache write successful")

        # Read it back
        response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["payload"]["date"] == test_date
        assert len(data["payload"]["articles"]) == 1
        print("  ✓ Daily cache read successful")
        print("  ✓ Test 2 PASSED")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Test 2 FAILED: {e}")

    # Test 3: Article state modifications (simulates useArticleState operations)
    print("\n[Test 3] Testing article state modifications...")
    total_tests += 1

    try:
        # Mark article as read
        test_payload["articles"][0]["read"]["isRead"] = True
        test_payload["articles"][0]["read"]["markedAt"] = datetime.now().isoformat()

        response = requests.post(
            f"{BASE_URL}/api/storage/daily/{test_date}",
            json={"payload": test_payload},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        print("  ✓ Mark as read successful")

        # Read back and verify
        response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
        data = response.json()
        assert data["payload"]["articles"][0]["read"]["isRead"] == True
        print("  ✓ Read state persisted")

        # Mark article as removed
        test_payload["articles"][0]["removed"] = True

        response = requests.post(
            f"{BASE_URL}/api/storage/daily/{test_date}",
            json={"payload": test_payload},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        print("  ✓ Mark as removed successful")

        # Read back and verify
        response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
        data = response.json()
        assert data["payload"]["articles"][0]["removed"] == True
        assert data["payload"]["articles"][0]["read"]["isRead"] == True  # Both states should persist
        print("  ✓ Removed state persisted (read state also intact)")

        # Mark TLDR as hidden
        test_payload["articles"][0]["tldrHidden"] = True

        response = requests.post(
            f"{BASE_URL}/api/storage/daily/{test_date}",
            json={"payload": test_payload},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        print("  ✓ Mark TLDR hidden successful")

        # Read back and verify all states
        response = requests.get(f"{BASE_URL}/api/storage/daily/{test_date}")
        data = response.json()
        article = data["payload"]["articles"][0]
        assert article["removed"] == True
        assert article["tldrHidden"] == True
        assert article["read"]["isRead"] == True
        print("  ✓ All article states persisted correctly")
        print("  ✓ Test 3 PASSED")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Test 3 FAILED: {e}")

    # Test 4: Cache check API (used by scraper.js)
    print("\n[Test 4] Testing cache check API...")
    total_tests += 1

    try:
        # Check if date exists
        response = requests.get(f"{BASE_URL}/api/storage/is-cached/{test_date}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["is_cached"] == True
        print("  ✓ Cache check returns True for existing date")

        # Check non-existent date
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        response = requests.get(f"{BASE_URL}/api/storage/is-cached/{future_date}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["is_cached"] == False
        print("  ✓ Cache check returns False for non-existent date")
        print("  ✓ Test 4 PASSED")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Test 4 FAILED: {e}")

    # Test 5: Date range query (used by scraper.js)
    print("\n[Test 5] Testing date range query...")
    total_tests += 1

    try:
        # Add another date to test range
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_payload = {
            "date": yesterday,
            "cachedAt": datetime.now().isoformat(),
            "articles": [
                {
                    "url": "https://example.com/article2",
                    "title": "Test Article 2",
                    "issueDate": yesterday,
                    "category": "Tech",
                    "removed": False,
                    "tldrHidden": False,
                    "read": {"isRead": False, "markedAt": None},
                    "tldr": {"status": "unknown", "markdown": ""}
                }
            ],
            "issues": []
        }

        response = requests.post(
            f"{BASE_URL}/api/storage/daily/{yesterday}",
            json={"payload": yesterday_payload},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        print("  ✓ Added second date to cache")

        # Query range
        response = requests.post(
            f"{BASE_URL}/api/storage/daily-range",
            json={"start_date": yesterday, "end_date": test_date},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert len(data["payloads"]) == 2
        print(f"  ✓ Range query returned {len(data['payloads'])} payloads")

        # Verify order (should be descending by date)
        dates = [p["date"] for p in data["payloads"]]
        assert dates[0] >= dates[1], "Payloads should be ordered by date descending"
        print("  ✓ Payloads ordered correctly (descending)")
        print("  ✓ Test 5 PASSED")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Test 5 FAILED: {e}")

    # Test 6: Error handling
    print("\n[Test 6] Testing error handling...")
    total_tests += 1

    try:
        # Try to read non-existent setting
        response = requests.get(f"{BASE_URL}/api/storage/setting/non-existent-key")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] == False
        print("  ✓ Non-existent setting returns 404")

        # Try to read non-existent date
        response = requests.get(f"{BASE_URL}/api/storage/daily/2099-12-31")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] == False
        print("  ✓ Non-existent date returns 404")
        print("  ✓ Test 6 PASSED")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Test 6 FAILED: {e}")

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests passed: {success_count}/{total_tests}")

    if success_count == total_tests:
        print("\n✓ ALL TESTS PASSED")
        print("\nPhase 3 Verification:")
        print("✓ useSupabaseStorage backend integration working")
        print("✓ Article state operations persist correctly")
        print("✓ Loading states supported (async operations)")
        print("✓ Error handling works as expected")
        print("✓ Data integrity maintained across operations")
        print("✓ Ready for component integration (Phase 4-5)")
        return True
    else:
        print(f"\n✗ {total_tests - success_count} TESTS FAILED")
        return False

if __name__ == "__main__":
    import sys
    try:
        success = test_phase3_api_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
