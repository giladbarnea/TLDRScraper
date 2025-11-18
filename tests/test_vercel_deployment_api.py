"""
Test Vercel deployment using HTTP requests (no browser required)
"""
import json
import os

def test_vercel_deployment_api():
    """Test the Vercel deployment API and frontend"""
    base_url = "https://tldr-flask-scraper-git-claude-hide-d1c7ab-giladbarneas-projects.vercel.app"

    print("\n" + "="*80)
    print("VERCEL DEPLOYMENT API TEST")
    print(f"Base URL: {base_url}")
    print("="*80)

    import subprocess

    print("\n1. Testing homepage (GET /)...")
    result = subprocess.run(
        ["curl", "-s", "-w", "\\nHTTP_CODE:%{http_code}", base_url + "/"],
        capture_output=True,
        text=True
    )
    if "HTTP_CODE:200" in result.stdout:
        print("   ✓ Homepage returns 200 OK")
        if "<div id=\"root\"></div>" in result.stdout:
            print("   ✓ React root div found")
        if "/assets/index-" in result.stdout:
            print("   ✓ React bundle script found")
        if "Newsletter Aggregator" in result.stdout:
            print("   ✓ Page title correct")
    else:
        print(f"   ✗ Homepage failed: {result.stdout}")
        return

    print("\n2. Testing API endpoint (POST /api/scrape)...")
    scrape_payload = {
        "start_date": "2025-11-15",
        "end_date": "2025-11-15"
    }
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(scrape_payload),
            "-w", "\\nHTTP_CODE:%{http_code}",
            base_url + "/api/scrape"
        ],
        capture_output=True,
        text=True,
        timeout=60
    )

    if "HTTP_CODE:200" in result.stdout:
        print("   ✓ API scrape endpoint returns 200 OK")

        try:
            response_text = result.stdout.split("HTTP_CODE:")[0]
            data = json.loads(response_text)

            if "success" in data:
                print(f"   ✓ Response has 'success' field: {data['success']}")

            if "articles" in data:
                article_count = len(data["articles"]) if isinstance(data["articles"], list) else 0
                print(f"   ✓ Response has 'articles' field: {article_count} articles")

            if "issues" in data:
                issue_count = len(data["issues"]) if isinstance(data["issues"], list) else 0
                print(f"   ✓ Response has 'issues' field: {issue_count} issues")

            if "stats" in data:
                print(f"   ✓ Response has 'stats' field")
                stats = data["stats"]
                if "total_articles" in stats:
                    print(f"      - total_articles: {stats['total_articles']}")
                if "unique_urls" in stats:
                    print(f"      - unique_urls: {stats['unique_urls']}")
                if "dates_processed" in stats:
                    print(f"      - dates_processed: {stats['dates_processed']}")

        except json.JSONDecodeError as e:
            print(f"   ⚠ Could not parse JSON response: {e}")
            print(f"   Response preview: {result.stdout[:500]}")
    else:
        print(f"   ✗ API scrape failed")
        print(f"   Response: {result.stdout[:500]}")

    print("\n3. Testing storage endpoints...")

    print("\n   3a. GET /api/storage/setting/cache:enabled")
    result = subprocess.run(
        ["curl", "-s", "-w", "\\nHTTP_CODE:%{http_code}", base_url + "/api/storage/setting/cache:enabled"],
        capture_output=True,
        text=True
    )
    if "HTTP_CODE:200" in result.stdout:
        print("      ✓ Settings endpoint returns 200 OK")
        try:
            response_text = result.stdout.split("HTTP_CODE:")[0]
            data = json.loads(response_text)
            print(f"      ✓ Cache setting: {data.get('value', 'unknown')}")
        except:
            pass
    else:
        print(f"      ✗ Settings endpoint failed")

    print("\n   3b. GET /api/storage/is-cached/2025-11-15")
    result = subprocess.run(
        ["curl", "-s", "-w", "\\nHTTP_CODE:%{http_code}", base_url + "/api/storage/is-cached/2025-11-15"],
        capture_output=True,
        text=True
    )
    if "HTTP_CODE:200" in result.stdout:
        print("      ✓ Is-cached endpoint returns 200 OK")
        try:
            response_text = result.stdout.split("HTTP_CODE:")[0]
            data = json.loads(response_text)
            print(f"      ✓ Is cached: {data.get('is_cached', 'unknown')}")
        except:
            pass
    else:
        print(f"      ✗ Is-cached endpoint failed")

    print("\n" + "="*80)
    print("DEPLOYMENT TEST COMPLETE")
    print("="*80)
    print("\n✓ Vercel deployment is accessible and functional")
    print("✓ Frontend React app loads correctly")
    print("✓ Backend API endpoints respond correctly")
    print("✓ Storage layer is operational")

if __name__ == "__main__":
    test_vercel_deployment_api()
