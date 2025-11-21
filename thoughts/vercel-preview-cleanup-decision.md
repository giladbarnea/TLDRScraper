# Vercel Preview Cleanup: Research & Decision

## Executive Summary

**Recommended Approach:** GitHub Actions (not git hooks)
**Implementation Method:** Vercel API (not CLI)

## The Fundamental Timing Issue

There's a crucial timing mismatch that affects the git hook decision:

```
Timeline of Events:
1. Developer makes local commits
2. Local git hooks run (post-merge, pre-merge-commit, etc.)
3. Developer runs: git push
4. pre-push hook runs (if configured)
5. Commits sent to GitHub
6. GitHub receives push
7. Vercel webhook triggers ← DEPLOYMENTS CREATED HERE
8. GitHub Actions runs (if configured) ← CLEANUP CAN HAPPEN HERE
```

**Key Insight:** All local git hooks (including `pre-push`) run BEFORE Vercel creates deployments. At the time any local hook executes:
- The NEW deployment doesn't exist yet (Vercel hasn't been notified)
- Only OLD deployments from previous pushes exist
- You're cleaning up yesterday's mess, not today's

## Research Findings

### Agent 1: Git Hook Investigation

**Key Discoveries:**
1. Vercel creates deployments **when commits are pushed to GitHub**, not when commits are created locally
2. Git has no native `post-push` hook
3. All commit-generating hooks run before push
4. By the time Vercel deploys, local git hooks have already finished

**Recommendation:** Use GitHub Actions triggered `on: push` instead of local git hooks

**Reasoning:**
- GitHub Actions runs AFTER push completes (when deployments exist)
- Centralized (all developers benefit without local setup)
- Handles all scenarios (commit, merge, rebase, force-push)
- Doesn't block legitimate pushes if cleanup fails

### Agent 2: CLI vs API Investigation

**Key Discoveries:**
1. Both Vercel CLI and API can accomplish the task
2. API has significant advantages for automation:
   - JSON output (easy parsing with `jq`)
   - Direct branch filtering: `?branch=<name>`
   - Reliable sorting by creation timestamp
   - No CLI installation required
   - Works in minimal/containerized environments

3. CLI limitations:
   - No JSON output (text parsing is fragile)
   - Output format can change between versions
   - Requires CLI installation

**Recommendation:** Use Vercel API

## Two Implementation Options

### Option A: GitHub Actions (RECOMMENDED)

**When it runs:** AFTER push, AFTER Vercel creates deployment

**How it works:**
1. Developer pushes to branch
2. Vercel creates new deployment
3. GitHub Actions triggers
4. Workflow queries Vercel API for all deployments on this branch
5. Sorts by creation time, keeps most recent
6. Deletes all older deployments
7. Result: Only the newest deployment remains

**Pros:**
- Correct timing (new deployment exists to be kept)
- Centralized (no local setup)
- Non-blocking (doesn't affect push)
- Handles edge cases (force-push, simultaneous pushes)
- No maintenance per developer

**Cons:**
- Slight delay (seconds to minutes) between deployment and cleanup
- Uses GitHub Actions minutes (minimal cost)
- Requires GitHub secrets configuration

**Files:**
- `.github/workflows/cleanup-vercel-previews.yml` (created)

**Setup Required:**
1. Add GitHub secrets:
   - `VERCEL_TOKEN` (from Vercel dashboard → Settings → Tokens)
   - `VERCEL_PROJECT_ID` (from project settings)
   - `VERCEL_TEAM_ID` (optional, for team projects)
2. Push the workflow file
3. Done - automatic for all developers

### Option B: Pre-Push Hook (ALTERNATIVE)

**When it runs:** BEFORE push, AFTER local commits

**How it works:**
1. Developer makes local commits
2. Developer runs `git push`
3. `pre-push` hook executes
4. Hook queries Vercel API for all deployments on this branch
5. Deletes all existing deployments (from previous pushes)
6. Push proceeds
7. Vercel creates ONE new deployment
8. Result: Only the newest deployment remains

**Pros:**
- More efficient (never creates temporary spike of N+1 deployments)
- Immediate cleanup before push
- Can be useful if you want to guarantee cleanup happens

**Cons:**
- Can block push if cleanup fails/times out
- Each developer must install hooks locally
- If push fails after cleanup, you've deleted deployments without creating new one
- Doesn't handle force-pushes well
- More fragile

**Files:**
- `.githooks/pre-push` (created)
- `scripts/cleanup-vercel-previews.sh` (created)

**Setup Required:**
1. Ensure `setup-hooks.sh` configures pre-push hook
2. Each developer must run `./setup-hooks.sh`
3. Environment variables needed:
   - `VERCEL_TOKEN`
   - `VERCEL_PROJECT_ID`
   - `VERCEL_TEAM_ID` (optional)

## Why Not Other Git Hooks?

**post-merge, post-checkout, post-rewrite, pre-rebase:**
- These run during local operations, before push
- Vercel hasn't deployed yet
- Too early for cleanup

**post-receive, post-update:**
- Server-side hooks (run on GitHub's servers)
- You don't control these with Vercel's setup

**pre-push:**
- Runs before push, so new deployment doesn't exist yet
- Can only clean up OLD deployments
- Still workable but has timing/reliability issues

## Clarification: Your Commit-Generating Hooks

You mentioned "multiple Git hooks that create commits in our current workflow." Important clarification:

**These hooks do NOT trigger Vercel deployments:**
- `pre-commit` hooks that format code
- `post-merge` hooks that update files
- `pre-merge-commit` hooks that generate files

**Only THIS triggers Vercel:**
- `git push` to GitHub

So the "after all commit-generating hooks finish" timing is actually BEFORE Vercel creates any deployment. Your commit-generating hooks are preparing the commits that will eventually be pushed, but Vercel doesn't see them until the push completes.

## Final Recommendation

**Use GitHub Actions** (Option A) because:

1. **Correct architecture:** Vercel deployments are remote resources that should be managed remotely
2. **Reliable timing:** Runs after new deployment exists
3. **Zero maintenance:** No per-developer setup
4. **Non-blocking:** Cleanup failures don't affect push
5. **Industry standard:** This is how most teams handle Vercel cleanup

## Implementation Commands

### To enable GitHub Actions approach:

```bash
# 1. Add GitHub secrets (via web UI or CLI)
gh secret set VERCEL_TOKEN --body "your-token-here"
gh secret set VERCEL_PROJECT_ID --body "prj_xxxxx"
gh secret set VERCEL_TEAM_ID --body "team_xxxxx"  # Optional

# 2. Commit and push the workflow
git add .github/workflows/cleanup-vercel-previews.yml
git commit -m "Add Vercel preview cleanup workflow"
git push

# 3. Done - automatic from now on
```

### To enable pre-push hook approach (if you prefer):

```bash
# 1. Ensure hooks are configured
./setup-hooks.sh

# 2. Verify pre-push hook is executable
ls -l .githooks/pre-push

# 3. Test manually
./scripts/cleanup-vercel-previews.sh "$(git rev-parse --abbrev-ref HEAD)"

# 4. Next push will automatically clean up
```

## Testing

### Test GitHub Actions:
```bash
# Push to a non-main branch
git checkout -b test-cleanup
git commit --allow-empty -m "Test cleanup"
git push -u origin test-cleanup

# Check GitHub Actions tab in repository
# Should see "Cleanup Vercel Preview Deployments" workflow running
```

### Test pre-push hook:
```bash
# Dry run (manual execution)
./scripts/cleanup-vercel-previews.sh "$(git rev-parse --abbrev-ref HEAD)"

# Real test
git push  # Hook will run automatically before push
```

## Monitoring

### Verify cleanup is working:

```bash
# List all deployments for current branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
curl -s "https://api.vercel.com/v6/deployments?projectId=$VERCEL_PROJECT_ID&branch=$BRANCH" \
  -H "Authorization: Bearer $VERCEL_TOKEN" | jq '.deployments | length'

# Should return 1 (only most recent)
```

## Alternative: Vercel Retention Policies

If you want automatic time-based cleanup without custom scripts:

1. Go to Vercel dashboard → Project Settings → Deployments
2. Configure retention policies:
   - Preview deployments: 1 day
   - Production: 30 days
3. Vercel will auto-delete after TTL expires

**Limitation:** This is time-based, not count-based. You can't guarantee "only keep most recent" - it's "delete after N days."

## Resources

- [Vercel Deployment API Docs](https://vercel.com/docs/rest-api/endpoints/deployments)
- [GitHub Actions - Workflow Syntax](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [Git Hooks Documentation](https://git-scm.com/docs/githooks)
- [Community Example: DEV.to Vercel Cleanup](https://dev.to/thereis/how-to-remove-vercel-deployments-from-github-actions-4nfh)
