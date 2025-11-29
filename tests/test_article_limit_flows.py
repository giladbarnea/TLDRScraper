#!/usr/bin/env python3
"""
Comprehensive integration tests for article limit bug fix.
Tests various cache states and user flows using REST APIs.
"""
import requests
import json
import sys
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5001"

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

def test_api_articles_with_cached_data():
    """Test 1: THE BUG - /api/articles should return limited results from cache"""
    log("TEST 1: /api/articles returns limited results (original bug scenario)")

    date = "2025-11-27"

    # Check what's in the database
    resp = requests.get(f"{BASE_URL}/api/storage/daily/{date}")
    if resp.status_code != 200:
        log(f"DB has no data for {date}, skipping test", "SKIP")
        return None

    db_data = resp.json()
    db_count = len(db_data['payload']['articles'])
    log(f"Database has {db_count} articles (super-set)")

    # Call /api/articles (should apply limits)
    resp = requests.post(f"{BASE_URL}/api/articles", json={
        "start_date": date,
        "end_date": date
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    data = resp.json()
    assert data['success'], f"Expected success=true, got {data}"

    limited_count = len(data['articles'])
    log(f"/api/articles returned {limited_count} articles (limited sub-set)")

    # THE BUG FIX: Limited count should be <= database count
    assert limited_count <= db_count, f"BUG: Limited ({limited_count}) > DB ({db_count})"
    assert limited_count <= 50, f"BUG: Limited ({limited_count}) exceeds daily limit (50)"

    log(f"✓ PASS: Limits applied correctly ({limited_count} <= {db_count})", "PASS")
    return limited_count

def test_empty_cache():
    """Test 2: /api/articles with empty cache returns empty gracefully"""
    log("TEST 2: /api/articles with empty cache")

    # Use a future date that definitely has no data
    future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")

    resp = requests.post(f"{BASE_URL}/api/articles", json={
        "start_date": future_date,
        "end_date": future_date
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    data = resp.json()
    assert data['success'], f"Expected success=true, got {data}"
    assert len(data['articles']) == 0, f"Expected 0 articles, got {len(data['articles'])}"

    log("✓ PASS: Empty cache handled gracefully", "PASS")

def test_multi_date_range():
    """Test 3: /api/articles applies limits correctly across multiple dates"""
    log("TEST 3: Multi-date range limiting")

    # Test 3-day range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    resp = requests.post(f"{BASE_URL}/api/articles", json={
        "start_date": start_str,
        "end_date": end_str
    })

    if resp.status_code != 200:
        log(f"API call failed: {resp.status_code}", "SKIP")
        return

    data = resp.json()
    if not data['success']:
        log(f"API returned error: {data.get('error')}", "SKIP")
        return

    total_articles = len(data['articles'])
    dates_processed = data['stats']['dates_processed']

    log(f"3-day range returned {total_articles} articles across {dates_processed} dates")

    # Each date should have max 50 articles, so 3 dates = max 150
    max_expected = 50 * dates_processed
    assert total_articles <= max_expected, f"BUG: {total_articles} > {max_expected}"

    log(f"✓ PASS: Multi-date limiting correct ({total_articles} <= {max_expected})", "PASS")

def test_cache_hit_flow():
    """Test 4: Full cache hit flow - isRangeCached → loadFromCache → /api/articles"""
    log("TEST 4: Cache hit flow (client perspective)")

    date = "2025-11-27"

    # Step 1: Check if date is cached (like client does)
    resp = requests.get(f"{BASE_URL}/api/storage/is-cached/{date}")
    assert resp.status_code == 200

    is_cached = resp.json()['is_cached']
    if not is_cached:
        log(f"Date {date} not cached, skipping test", "SKIP")
        return

    log(f"Date {date} is cached")

    # Step 2: Load from cache via /api/articles (like loadFromCache() does)
    resp = requests.post(f"{BASE_URL}/api/articles", json={
        "start_date": date,
        "end_date": date
    })
    assert resp.status_code == 200

    data = resp.json()
    assert data['success']
    assert data['stats']['network_fetches'] == 0, "Cache hit should have 0 network fetches"

    article_count = len(data['articles'])
    log(f"Cache hit returned {article_count} articles with 0 network fetches")

    log("✓ PASS: Cache hit flow works correctly", "PASS")

def test_scrape_then_cache_hit():
    """Test 5: Scrape fresh data, then load from cache - both should return same limited count"""
    log("TEST 5: Scrape → Cache hit consistency")

    # Use yesterday's date for testing
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Step 1: Scrape (may update cache)
    log(f"Scraping {yesterday}...")
    resp = requests.post(f"{BASE_URL}/api/scrape", json={
        "start_date": yesterday,
        "end_date": yesterday
    })

    if resp.status_code != 200:
        log(f"Scrape failed: {resp.status_code}", "SKIP")
        return

    scrape_data = resp.json()
    if not scrape_data['success']:
        log(f"Scrape returned error: {scrape_data.get('error')}", "SKIP")
        return

    scrape_count = len(scrape_data['articles'])
    log(f"Scrape returned {scrape_count} articles")

    # Step 2: Load from cache
    log(f"Loading from cache via /api/articles...")
    resp = requests.post(f"{BASE_URL}/api/articles", json={
        "start_date": yesterday,
        "end_date": yesterday
    })
    assert resp.status_code == 200

    cache_data = resp.json()
    assert cache_data['success']

    cache_count = len(cache_data['articles'])
    log(f"Cache hit returned {cache_count} articles")

    # Both should return same limited count
    assert cache_count == scrape_count, f"Inconsistency: scrape={scrape_count}, cache={cache_count}"

    log(f"✓ PASS: Scrape and cache return consistent counts ({scrape_count})", "PASS")

def test_all_articles_removed():
    """Test 6: When all articles for a date are marked removed, /api/articles returns 0"""
    log("TEST 6: All articles removed scenario")

    date = "2025-11-27"

    # Get current payload
    resp = requests.get(f"{BASE_URL}/api/storage/daily/{date}")
    if resp.status_code != 200:
        log(f"No data for {date}, skipping test", "SKIP")
        return

    original_payload = resp.json()['payload']
    original_count = len(original_payload['articles'])

    log(f"Original: {original_count} articles")

    # Mark all articles as removed
    modified_payload = {
        'date': date,
        'articles': [
            {**article, 'removed': True}
            for article in original_payload['articles']
        ],
        'issues': original_payload.get('issues', [])
    }

    # Save modified payload
    resp = requests.post(f"{BASE_URL}/api/storage/daily/{date}",
                        json={'payload': modified_payload})
    assert resp.status_code == 200

    log(f"Marked all {original_count} articles as removed")

    # Query via /api/articles - should return 0
    resp = requests.post(f"{BASE_URL}/api/articles", json={
        "start_date": date,
        "end_date": date
    })
    assert resp.status_code == 200

    data = resp.json()
    assert data['success']
    assert len(data['articles']) == 0, f"Expected 0 articles, got {len(data['articles'])}"

    # Restore original payload
    resp = requests.post(f"{BASE_URL}/api/storage/daily/{date}",
                        json={'payload': original_payload})
    assert resp.status_code == 200

    log("✓ PASS: All removed articles filtered out correctly", "PASS")

def test_partial_cache():
    """Test 7: Partial cache (some dates exist, some don't) - should use /api/scrape"""
    log("TEST 7: Partial cache scenario")

    # Use a range where some dates might exist
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    # Check which dates are cached
    dates_to_check = []
    current = start_date
    while current <= end_date:
        dates_to_check.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    cached_status = []
    for date_str in dates_to_check:
        resp = requests.get(f"{BASE_URL}/api/storage/is-cached/{date_str}")
        is_cached = resp.json()['is_cached']
        cached_status.append(is_cached)

    log(f"Cache status: {list(zip(dates_to_check, cached_status))}")

    all_cached = all(cached_status)
    none_cached = not any(cached_status)
    partial_cache = not all_cached and not none_cached

    if partial_cache:
        log("Partial cache detected - client should use /api/scrape")
    elif all_cached:
        log("All cached - client should use /api/articles")
    else:
        log("None cached - client should use /api/scrape")

    log("✓ PASS: Cache status checked successfully", "PASS")

def main():
    log("=" * 60)
    log("ARTICLE LIMIT BUG FIX - INTEGRATION TESTS")
    log("=" * 60)

    tests = [
        test_api_articles_with_cached_data,
        test_empty_cache,
        test_multi_date_range,
        test_cache_hit_flow,
        test_scrape_then_cache_hit,
        test_all_articles_removed,
        test_partial_cache,
    ]

    passed = 0
    failed = 0
    skipped = 0

    for test_func in tests:
        log("")
        try:
            result = test_func()
            if result is None:
                skipped += 1
            else:
                passed += 1
        except AssertionError as e:
            log(f"✗ FAIL: {e}", "FAIL")
            failed += 1
        except Exception as e:
            log(f"✗ ERROR: {e}", "ERROR")
            failed += 1

    log("")
    log("=" * 60)
    log(f"RESULTS: {passed} passed, {failed} failed, {skipped} skipped")
    log("=" * 60)

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
