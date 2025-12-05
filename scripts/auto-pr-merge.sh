#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/auto-pr-merge.sh <branch-name> "<commit-message>"
# Example: ./scripts/auto-pr-merge.sh fix-bug "Fix navigation bug"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <branch-name> <commit-message> [pr-title] [pr-body]"
    echo "Example: $0 fix-bug 'Fix navigation bug' 'Fix nav' 'Fixes #123'"
    exit 1
fi

BRANCH_NAME="$1"
COMMIT_MESSAGE="$2"
PR_TITLE="${3:-$COMMIT_MESSAGE}"
PR_BODY="${4:-}"

echo "🚀 Starting automated PR workflow for branch: $BRANCH_NAME"

# 1. Create and checkout branch
echo "📝 Creating branch..."
git checkout -b "$BRANCH_NAME"

# 2. Add all changes and commit
echo "💾 Committing changes..."
git add -A
git commit -m "$COMMIT_MESSAGE"

# 3. Push to remote
echo "⬆️  Pushing to remote..."
git push -u origin "$BRANCH_NAME"

# 4. Create PR
echo "🔀 Creating pull request..."
if [ -z "$PR_BODY" ]; then
    PR_BODY="$(cat <<EOF
## Summary
$COMMIT_MESSAGE
EOF
)"
fi

PR_URL=$(gh pr create --title "$PR_TITLE" --body "$PR_BODY")
PR_NUMBER=$(echo "$PR_URL" | grep -o '[0-9]\+$')

echo "✅ PR created: $PR_URL"

# 5. Poll for workflow completion
echo "⏳ Polling for workflow completion..."
MAX_WAIT=600  # 10 minutes max
POLL_INTERVAL=10  # Check every 10 seconds
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Get workflow status
    CHECKS_OUTPUT=$(gh pr checks "$PR_NUMBER" 2>&1 || true)

    # Check if any workflows are still pending
    if echo "$CHECKS_OUTPUT" | grep -q "pending\|in_progress\|queued"; then
        echo "⏳ Workflows still running... (${ELAPSED}s elapsed)"
        sleep $POLL_INTERVAL
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
        continue
    fi

    # Check if any workflows failed
    if echo "$CHECKS_OUTPUT" | grep -q "fail"; then
        echo "❌ Workflow checks failed:"
        echo "$CHECKS_OUTPUT"
        echo ""
        echo "PR URL: $PR_URL"
        exit 1
    fi

    # All checks passed
    if echo "$CHECKS_OUTPUT" | grep -qE "pass|skipping|success"; then
        echo "✅ All workflow checks passed!"
        break
    fi

    # Fallback - wait a bit more
    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "⏱️  Timeout waiting for workflows (${MAX_WAIT}s)"
    echo "PR URL: $PR_URL"
    exit 1
fi

# 6. Merge PR
echo "🔀 Merging PR..."
gh pr merge "$PR_NUMBER" --squash --delete-branch

echo "🎉 Successfully merged PR #$PR_NUMBER and deleted remote branch"
echo "🔄 Switching back to main..."
git checkout main
git pull

echo "✅ All done!"
