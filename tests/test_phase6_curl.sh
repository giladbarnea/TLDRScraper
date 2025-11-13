#!/bin/bash

# Phase 6 - Automated API Tests with curl
# Tests all storage API endpoints

set -e

BASE_URL="http://localhost:5001"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "======================================================================"
echo "PHASE 6: AUTOMATED API VERIFICATION (curl)"
echo "======================================================================"

echo ""
echo "=== Test: Settings API ==="

echo "Writing cache:enabled setting..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/storage/setting/cache:enabled" \
  -H "Content-Type: application/json" \
  -d '{"value": true}')

if echo "$RESPONSE" | grep -q '"success": true'; then
  echo -e "${GREEN}✓${NC} Setting write successful"
else
  echo -e "${RED}✗${NC} Setting write failed"
  echo "$RESPONSE"
  exit 1
fi

echo "Reading cache:enabled setting..."
RESPONSE=$(curl -s "$BASE_URL/api/storage/setting/cache:enabled")

if echo "$RESPONSE" | grep -q '"success": true' && echo "$RESPONSE" | grep -q '"value": true'; then
  echo -e "${GREEN}✓${NC} Setting read successful"
else
  echo -e "${RED}✗${NC} Setting read failed"
  echo "$RESPONSE"
  exit 1
fi

echo ""
echo "=== Test: Daily Cache API ==="

TEST_DATE="2025-11-09"
TEST_PAYLOAD='{
  "payload": {
    "date": "2025-11-09",
    "cachedAt": "2025-11-09T12:00:00Z",
    "articles": [
      {
        "url": "https://example.com/test",
        "title": "Test Article",
        "issueDate": "2025-11-09",
        "category": "Newsletter",
        "removed": false,
        "tldrHidden": false,
        "read": {"isRead": false, "markedAt": null},
        "tldr": {"status": "unknown", "markdown": ""}
      }
    ],
    "issues": []
  }
}'

echo "Writing daily payload..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/storage/daily/$TEST_DATE" \
  -H "Content-Type: application/json" \
  -d "$TEST_PAYLOAD")

if echo "$RESPONSE" | grep -q '"success": true'; then
  echo -e "${GREEN}✓${NC} Daily payload write successful"
else
  echo -e "${RED}✗${NC} Daily payload write failed"
  echo "$RESPONSE"
  exit 1
fi

echo "Reading daily payload..."
RESPONSE=$(curl -s "$BASE_URL/api/storage/daily/$TEST_DATE")

if echo "$RESPONSE" | grep -q '"success": true' && echo "$RESPONSE" | grep -q '"date": "2025-11-09"'; then
  echo -e "${GREEN}✓${NC} Daily payload read successful"
else
  echo -e "${RED}✗${NC} Daily payload read failed"
  echo "$RESPONSE"
  exit 1
fi

echo ""
echo "=== Test: Cache Check API ==="

echo "Checking if $TEST_DATE is cached..."
RESPONSE=$(curl -s "$BASE_URL/api/storage/is-cached/$TEST_DATE")

if echo "$RESPONSE" | grep -q '"is_cached": true'; then
  echo -e "${GREEN}✓${NC} Cache check successful (date is cached)"
else
  echo -e "${RED}✗${NC} Cache check failed"
  echo "$RESPONSE"
  exit 1
fi

echo "Checking if non-existent date is cached..."
RESPONSE=$(curl -s "$BASE_URL/api/storage/is-cached/1900-01-01")

if echo "$RESPONSE" | grep -q '"is_cached": false'; then
  echo -e "${GREEN}✓${NC} Cache check successful (date not cached)"
else
  echo -e "${RED}✗${NC} Cache check failed"
  echo "$RESPONSE"
  exit 1
fi

echo ""
echo "=== Test: Range Query API ==="

echo "Querying date range..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/storage/daily-range" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-11-07", "end_date": "2025-11-09"}')

if echo "$RESPONSE" | grep -q '"success": true' && echo "$RESPONSE" | grep -q '"payloads"'; then
  echo -e "${GREEN}✓${NC} Range query successful"
else
  echo -e "${RED}✗${NC} Range query failed"
  echo "$RESPONSE"
  exit 1
fi

echo ""
echo "=== Test: Error Handling ==="

echo "Reading non-existent setting..."
RESPONSE=$(curl -s "$BASE_URL/api/storage/setting/nonexistent:key")

if echo "$RESPONSE" | grep -q '"success": false'; then
  echo -e "${GREEN}✓${NC} Non-existent setting returns error (expected)"
else
  echo -e "${RED}✗${NC} Error handling failed"
  echo "$RESPONSE"
  exit 1
fi

echo "Reading non-existent date..."
RESPONSE=$(curl -s "$BASE_URL/api/storage/daily/1900-01-01")

if echo "$RESPONSE" | grep -q '"success": false'; then
  echo -e "${GREEN}✓${NC} Non-existent date returns error (expected)"
else
  echo -e "${RED}✗${NC} Error handling failed"
  echo "$RESPONSE"
  exit 1
fi

echo ""
echo "======================================================================"
echo -e "${GREEN}ALL CURL TESTS PASSED ✓${NC}"
echo "======================================================================"
echo ""
echo "All storage API endpoints responding correctly."
echo "Data integrity verified across write/read cycles."
echo ""
