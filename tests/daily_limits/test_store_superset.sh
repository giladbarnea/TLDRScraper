#!/usr/bin/env bash
# Tests the "Store Super-Set, Serve Sub-Set" implementation.
# Run from project root: ./tests/test_store_superset.sh

set -eo pipefail

source ./setup.sh

echo "=== 1. Doctests ==="
uv run python3 -m doctest util.py -v 2>&1 | tail -5
uv run python3 -m doctest newsletter_limiter.py -v 2>&1 | tail -5

echo -e "\n=== 2. Syntax check ==="
uv run python3 -m py_compile newsletter_scraper.py && echo "newsletter_scraper.py: OK"

echo -e "\n=== 3. Start server ==="
start_server_and_watchdog
sleep 3

cleanup() { kill_server_and_watchdog 2>/dev/null || true; }
trap cleanup EXIT

echo -e "\n=== 4. Scrape single date ==="
TODAY=$(date +%Y-%m-%d)
RESPONSE=$(curl -s http://localhost:5001/api/scrape -X POST \
  -H "Content-Type: application/json" \
  -d "{\"start_date\": \"$TODAY\", \"end_date\": \"$TODAY\", \"source_ids\": [\"tldr_tech\"]}")

SERVED=$(echo "$RESPONSE" | jq '.articles | length')
echo "Served (sub-set): $SERVED articles"

echo -e "\n=== 5. Verify DB super-set ==="
STORED=$(curl -s "http://localhost:5001/api/storage/daily/$TODAY" | jq '.payload.articles | length')
echo "Stored (super-set): $STORED articles"

echo -e "\n=== 6. Validate ==="
if [[ "$STORED" -ge "$SERVED" ]]; then
  echo "PASS: DB stores super-set ($STORED) >= served sub-set ($SERVED)"
else
  echo "FAIL: Expected stored >= served, got $STORED < $SERVED"
  exit 1
fi

echo -e "\n=== 7. Check logs for merge/save ==="
grep -E "(Merged to|Saved super-set)" .run/server.log | tail -2

echo -e "\nAll checks passed."
