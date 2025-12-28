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
if ! command -v git_current_branch 2>/dev/null; then
  git_current_branch() {
    local ref
    ref=$(GIT_OPTIONAL_LOCKS=0 command git symbolic-ref --quiet HEAD 2>/dev/null)
    local ret=$?
    if [[ $ret != 0 ]]; then
      [[ $ret == 128 ]] && return
      ref=$(GIT_OPTIONAL_LOCKS=0 command git rev-parse --short HEAD 2>/dev/null) || return
    fi
    echo ${ref#refs/heads/}
  }
fi

# 1. Create and checkout branch
if [[ "$(git_current_branch)" = "$BRANCH_NAME" ]]; then
  :
else
  echo "📝 Creating branch..."
  git checkout -b "$BRANCH_NAME"
fi
# 2. Add all changes and commit
echo "💾 Committing changes..."
git add -A
git commit -m "$COMMIT_MESSAGE"

# 3. Push to remote
echo "⬆️  Pushing to remote..."
git push -u origin "$BRANCH_NAME"

# 4. Check if PR already exists for this branch
echo "🔍 Checking if PR already exists..."
PR_INFO=$(gh pr view "$BRANCH_NAME" --json state,number,url 2>/dev/null || echo "")

if [ -n "$PR_INFO" ]; then
  PR_STATE=$(echo "$PR_INFO" | jq -r '.state')
  PR_NUMBER=$(echo "$PR_INFO" | jq -r '.number')
  PR_URL=$(echo "$PR_INFO" | jq -r '.url')

  if [ "$PR_STATE" = "MERGED" ] || [ "$PR_STATE" = "CLOSED" ]; then
    echo "❌ PR #$PR_NUMBER already exists and is $PR_STATE"
    echo "   URL: $PR_URL"
    exit 1
  fi

  echo "✅ Found existing open PR #$PR_NUMBER, will poll and merge it"
  echo "   URL: $PR_URL"
else
  # 5. Create PR
  echo "🔀 Creating pull request..."
  if [ -z "$PR_BODY" ]; then
    PR_BODY="$(
      cat <<EOF
## Summary
$COMMIT_MESSAGE
EOF
    )"
  fi

  PR_URL=$(gh pr create --title "$PR_TITLE" --body "$PR_BODY")
  PR_NUMBER=$(echo "$PR_URL" | grep -o '[0-9]\+$')

  echo "✅ PR created: $PR_URL"
fi

# 6. Poll for workflow completion
echo "⏳ Polling for workflow completion..."
MAX_WAIT=600     # 10 minutes max
POLL_INTERVAL=10 # Check every 10 seconds
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

# 7. Merge PR
echo "🔀 Merging PR..."
gh pr merge "$PR_NUMBER" --squash --delete-branch

echo "🎉 Successfully merged PR #$PR_NUMBER and deleted remote branch"
echo "🔄 Switching back to main..."
git checkout main
git pull

echo "✅ All done!"
