---
last_updated: 2026-01-05 06:10
---
# Documentation Maintenance Workflow

This diagram illustrates the sequential job execution in `maintain-documentation.yml` that prevents race conditions.

## Workflow Trigger Events

```
Push to main
    OR
PR opened/updated/reopened/merged to main
    ↓
┌───────────────────────────────────────────────────────────────┐
│ GitHub Actions: maintain-documentation.yml                    │
└───────────────────────────────────────────────────────────────┘
```

## Sequential Job Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ JOB 1: update-frontmatter                                       │
│ ════════════════════════════════════════════════════════════    │
│ • Checkout code                                                 │
│ • Run scripts/update_doc_frontmatter.py                         │
│ • Detect modified *.md files (excluding PROJECT_STRUCTURE.md)   │
│ • Update YAML frontmatter: last_updated: timestamp, commit_hash │
│ • Commit: "chore: Update doc frontmatter [skip ci]"             │
│ • Push to branch                                                │
│                                                                 │
│ Outputs:                                                        │
│   • modified_files: "AGENTS.md,ARCHITECTURE.md,..."            │
│   • has_changes: true/false                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                         needs: [update-frontmatter]
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ JOB 2: sync-agents-to-claude                                    │
│ ════════════════════════════════════════════════════════════    │
│ Condition: Job 1 succeeded AND AGENTS.md in modified_files      │
│                                                                 │
│ • Checkout code (includes Job 1 frontmatter updates!)           │
│ • cp AGENTS.md CLAUDE.md                                        │
│ • Commit: "chore: Sync CLAUDE.md with AGENTS.md [skip ci]"     │
│ • Push to branch                                                │
│                                                                 │
│ Why sequential?                                                 │
│   Previously, this job ran in parallel with Job 1, causing:    │
│   - Job 1 adds frontmatter to AGENTS.md                         │
│   - Job 2 reads OLD AGENTS.md (without frontmatter)             │
│   - CLAUDE.md ends up missing frontmatter → DESYNC!             │
│                                                                 │
│   Now: Job 2 always reads AGENTS.md AFTER frontmatter update    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                         needs: [sync-agents-to-claude]
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ JOB 3: generate-structure-preview                               │
│ ════════════════════════════════════════════════════════════    │
│ Condition: Job 2 completed (success or skipped)                 │
│                                                                 │
│ • Checkout code (includes all previous updates!)                │
│ • Set up Python 3.11                                            │
│ • Generate PROJECT_STRUCTURE.md (Python script)                 │
│ • Display preview in workflow logs                              │
│ • Do NOT commit (file is .gitignored)                           │
│                                                                 │
│ Why last?                                                       │
│   Generates preview after all mutations complete, reflecting    │
│   the final state of the repository                             │
└─────────────────────────────────────────────────────────────────┘
```

## Race Condition Prevention

### Before (Parallel Execution)

```
Trigger Event
    ├──► Job A: update-frontmatter ──► Push @ T+30s ──► Commit: abc123
    ├──► Job B: copy-agents         ──► Push @ T+25s ──► Commit: def456
    └──► Job C: generate-structure  ──► (no commit)

Problem: Jobs A & B run in parallel, both checkout same commit
         Job B copies AGENTS.md BEFORE Job A adds frontmatter
         Result: CLAUDE.md missing frontmatter (DESYNC!)

Additional Problem: Git push conflicts when both try to push
         One push succeeds, other gets "rejected non-fast-forward"
```

### After (Sequential Execution)

```
Trigger Event
    ↓
Job 1: update-frontmatter ──► Push ──► Commit: abc123
    ↓ (waits for completion)
Job 2: sync-agents-to-claude ──► Checkout abc123 ──► Push ──► Commit: def456
    ↓ (waits for completion)
Job 3: generate-structure-preview ──► Checkout def456 ──► (no commit)

Benefits:
✓ Each job sees previous job's changes
✓ No race condition (sequential execution)
✓ No push conflicts (one push at a time)
✓ AGENTS.md and CLAUDE.md stay in sync
✓ Explicit dependencies visible in workflow YAML
```

## Local Git Hooks

Local hooks remain independent and generate PROJECT_STRUCTURE.md for local development:

```
Git Operation          Hook Triggered       Actions
─────────────────────  ───────────────────  ────────────────────────────
git merge              pre-merge-commit     • Generate PROJECT_STRUCTURE.md
                       post-merge           • Configure merge.ours driver

git checkout <branch>  post-checkout        • Configure merge.ours driver
                                            • Generate PROJECT_STRUCTURE.md

git rebase             post-rewrite         • Configure merge.ours driver
git commit --amend
```

### Removed Redundancies

- **pre-rebase**: Deleted entirely (redundant with post-checkout)
- **post-merge**: No longer generates PROJECT_STRUCTURE.md (redundant with pre-merge-commit)
- **post-rewrite**: No longer generates PROJECT_STRUCTURE.md (redundant, runs per commit)

## Key Design Principles

1. **Explicit Sequential Dependencies**: Use `needs:` to enforce job order
2. **Conditional Execution**: Skip jobs when irrelevant (e.g., skip sync-agents if AGENTS.md unchanged)
3. **Single Source of Truth**: One consolidated workflow instead of three separate workflows
4. **No Race Conditions**: Each job waits for previous job to complete and push
5. **Idempotent Operations**: Each job can safely re-run without side effects
6. **Clear Separation**: Local hooks handle local dev, GitHub Actions handle remote automation

---

# Weekly Branch & PR Cleanup Workflow

This workflow runs every Sunday at 2 AM UTC to clean up stale branches and PRs.

## Workflow Steps

The workflow has three sequential steps:

### 1. Delete branches for old merged/closed PRs (1 week threshold)
- Gets all remote branches except main/master
- For each branch with an associated PR, checks if the PR is merged or closed
- Deletes the branch if the PR was completed more than 1 week ago

### 2. Delete orphan branches older than 2 weeks
- Skips branches that have any associated PR (those are handled by step 1)
- For branches without PRs, checks the last commit date
- Deletes if older than 2 weeks

### 3. Close stale open PRs (1 week threshold)
- Gets all open PRs in the repository
- Checks each PR's creation date
- Closes PR with an automated comment if created more than 1 week ago
