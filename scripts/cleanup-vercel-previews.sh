#!/bin/bash
set -euo pipefail

BRANCH_NAME="${1:-}"
PROJECT_ID="${VERCEL_PROJECT_ID:-}"
TEAM_ID="${VERCEL_TEAM_ID:-}"
VERCEL_TOKEN="${VERCEL_TOKEN:-}"
KEEP_RECENT="${KEEP_RECENT:-1}"

if [ -z "$BRANCH_NAME" ] || [ -z "$PROJECT_ID" ] || [ -z "$VERCEL_TOKEN" ]; then
    echo "Error: Missing required parameters" >&2
    echo "Usage: VERCEL_PROJECT_ID=xxx VERCEL_TOKEN=xxx $0 <branch-name>" >&2
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed" >&2
    exit 1
fi

API_URL="https://api.vercel.com/v6/deployments?projectId=$PROJECT_ID&branch=$BRANCH_NAME&limit=100"
[ -n "$TEAM_ID" ] && API_URL="$API_URL&teamId=$TEAM_ID"

echo "Fetching deployments for branch '$BRANCH_NAME'..."

RESPONSE=$(curl -sf -X GET "$API_URL" \
    -H "Authorization: Bearer $VERCEL_TOKEN") || {
    echo "Error: Failed to fetch deployments from Vercel API" >&2
    exit 1
}

DEPLOYMENT_IDS=$(echo "$RESPONSE" | \
    jq -r --arg keep "$KEEP_RECENT" \
    '.deployments | sort_by(.created) | .[0:-($keep|tonumber)] | .[].uid')

if [ -z "$DEPLOYMENT_IDS" ]; then
    echo "No old deployments to delete."
    exit 0
fi

COUNT=$(echo "$DEPLOYMENT_IDS" | wc -w)
echo "Found $COUNT deployment(s) to delete (keeping $KEEP_RECENT most recent)"

DELETED=0
FAILED=0

while IFS= read -r DEPLOYMENT_ID; do
    [ -z "$DEPLOYMENT_ID" ] && continue

    DELETE_URL="https://api.vercel.com/v13/deployments/$DEPLOYMENT_ID"
    [ -n "$TEAM_ID" ] && DELETE_URL="$DELETE_URL?teamId=$TEAM_ID"

    RESULT=$(curl -sf -X DELETE "$DELETE_URL" \
        -H "Authorization: Bearer $VERCEL_TOKEN" 2>&1) || {
        echo "  ✗ Failed: $DEPLOYMENT_ID"
        ((FAILED++))
        continue
    }

    STATE=$(echo "$RESULT" | jq -r '.state // empty')
    if [ "$STATE" = "DELETED" ]; then
        echo "  ✓ Deleted: $DEPLOYMENT_ID"
        ((DELETED++))
    else
        echo "  ✗ Unexpected response for $DEPLOYMENT_ID: $RESULT"
        ((FAILED++))
    fi
done <<< "$DEPLOYMENT_IDS"

echo "Cleanup complete: $DELETED deleted, $FAILED failed"
[ $FAILED -gt 0 ] && exit 1
exit 0
