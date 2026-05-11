#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/dev/auto-pr-merge.sh [-m MSG] [-t TITLE] [-b BODY] [-p PR] [step...]
#
# Composable building blocks for committing, pushing, creating a PR,
# waiting for CI, and merging. Run one or more steps in order.
#
# Steps:
#   commit  Stage all files, create a commit (no-op if tree is clean)
#   push    Push the current branch to origin and set upstream
#   pr      Create a pull request, or reuse an existing open PR for the branch
#   wait    Poll CI checks until all pass (timeout: 10 min)
#   merge   Squash-merge the PR, delete the remote branch, checkout main
#
# If no steps are given, defaults to: commit push pr wait merge
#
# Examples:
#   # Full flow from dirty worktree:
#   scripts/dev/auto-pr-merge.sh -m "fix bug"
#
#   # Already committed, just push, PR, wait, merge:
#   scripts/dev/auto-pr-merge.sh -m "fix bug" push pr wait merge
#
#   # PR already exists — just wait and merge:
#   scripts/dev/auto-pr-merge.sh wait merge
#   # Same, but skip the branch lookup:
#   scripts/dev/auto-pr-merge.sh -p 665 wait merge

# ── State ────────────────────────────────────────────────────────────────────
MESSAGE=""
TITLE=""
BODY=""
PR_NUMBER=""
PR_URL=""
BRANCH=$(git branch --show-current)
STEPS=()

MAX_WAIT=600
POLL_INTERVAL=10

# ── Helpers ──────────────────────────────────────────────────────────────────

usage() {
  sed -n '2,21p' "$0"
  exit 0
}

lookup_pr() {
  local info
  info=$(gh pr view "$BRANCH" --json state,number,url 2>/dev/null || echo "")
  if [[ -z "$info" ]]; then
    echo "❌ No PR found for branch '$BRANCH'"
    exit 1
  fi
  PR_STATE=$(echo "$info" | jq -r '.state')
  PR_NUMBER=$(echo "$info" | jq -r '.number')
  PR_URL=$(echo "$info" | jq -r '.url')
  if [[ "$PR_STATE" = "MERGED" || "$PR_STATE" = "CLOSED" ]]; then
    echo "❌ PR #$PR_NUMBER for '$BRANCH' is $PR_STATE"
    exit 1
  fi
}

require_message() {
  if [[ -z "$MESSAGE" ]]; then
    echo "❌ -m <message> is required when running 'commit'"
    exit 1
  fi
}

# ── Steps ────────────────────────────────────────────────────────────────────

do_commit() {
  require_message
  git add -A
  if git diff --cached --quiet; then
    echo "📭 Nothing to commit — worktree is clean"
    return 0
  fi
  echo "💾 Committing changes..."
  git commit -m "$MESSAGE"
}

do_push() {
  echo "⬆️  Pushing to origin..."
  git push -u origin "$BRANCH"
}

do_pr() {
  echo "🔍 Checking for existing PR on '$BRANCH'..."
  local info
  info=$(gh pr view "$BRANCH" --json state,number,url 2>/dev/null || echo "")

  if [[ -n "$info" ]]; then
    PR_STATE=$(echo "$info" | jq -r '.state')
    PR_NUMBER=$(echo "$info" | jq -r '.number')
    PR_URL=$(echo "$info" | jq -r '.url')

    if [[ "$PR_STATE" = "MERGED" || "$PR_STATE" = "CLOSED" ]]; then
      echo "❌ PR #$PR_NUMBER already exists and is $PR_STATE"
      echo "   URL: $PR_URL"
      exit 1
    fi

    echo "✅ Reusing existing open PR #$PR_NUMBER"
    echo "   URL: $PR_URL"
    return 0
  fi

  echo "🔀 Creating pull request..."
  local title="${TITLE:-$MESSAGE}"
  local body="$BODY"
  if [[ -z "$body" ]]; then
    body="## Summary
${MESSAGE}"
  fi

  PR_URL=$(gh pr create --title "$title" --body "$body")
  PR_NUMBER=$(echo "$PR_URL" | grep -o '[0-9]\+$')
  echo "✅ PR created: $PR_URL"
}

do_wait() {
  if [[ -z "$PR_NUMBER" ]]; then
    if [[ -n "${1:-}" ]]; then
      PR_NUMBER="$1"
    else
      lookup_pr
    fi
  fi

  echo "⏳ Polling CI for PR #$PR_NUMBER..."
  local elapsed=0

  while [[ $elapsed -lt $MAX_WAIT ]]; do
    local checks
    checks=$(gh pr checks "$PR_NUMBER" 2>&1 || true)

    if echo "$checks" | grep -q "pending\|in_progress\|queued"; then
      echo "⏳ Still running... (${elapsed}s)"
      sleep "$POLL_INTERVAL"
      elapsed=$((elapsed + POLL_INTERVAL))
      continue
    fi

    if echo "$checks" | grep -q "fail"; then
      echo "❌ CI checks failed:"
      echo "$checks"
      exit 1
    fi

    if echo "$checks" | grep -qE "pass|skipping|success"; then
      echo "✅ All checks passed!"
      return 0
    fi

    sleep "$POLL_INTERVAL"
    elapsed=$((elapsed + POLL_INTERVAL))
  done

  echo "⏱️  Timeout waiting for CI (${MAX_WAIT}s)"
  exit 1
}

do_merge() {
  if [[ -z "$PR_NUMBER" ]]; then
    lookup_pr
  fi

  echo "🔀 Squash-merging PR #$PR_NUMBER..."
  gh pr merge "$PR_NUMBER" --squash --delete-branch

  echo "🎉 Merged PR #$PR_NUMBER and deleted remote branch"
  echo "🔄 Switching to main..."
  git checkout main
  git pull
  echo "✅ All done!"
}

# ── Parse ────────────────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m) MESSAGE="$2"; shift 2 ;;
    -t) TITLE="$2"; shift 2 ;;
    -b) BODY="$2"; shift 2 ;;
    -p) PR_NUMBER="$2"; shift 2 ;;
    -h|--help) usage ;;
    commit|push|pr|wait|merge) STEPS+=("$1"); shift ;;
    *) echo "Unknown argument: $1"; usage ;;
  esac
done

if [[ ${#STEPS[@]} -eq 0 ]]; then
  STEPS=(commit push pr wait merge)
fi

# ── Run ──────────────────────────────────────────────────────────────────────

echo "🚀 Branch: $BRANCH  |  Steps: ${STEPS[*]}"
echo ""

for step in "${STEPS[@]}"; do
  case "$step" in
    commit) do_commit ;;
    push)   do_push ;;
    pr)     do_pr ;;
    wait)   do_wait ;;
    merge)  do_merge ;;
  esac
done
