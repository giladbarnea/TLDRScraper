---
last_updated: 2026-04-16 06:44
---
# Documentation Maintenance Workflow

This diagram illustrates the sequential job execution in `maintain-documentation.yml` that prevents race conditions.

## Workflow Trigger Events

```
Push to main
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
│ • cp AGENTS.md CLAUDE.md GEMINI.md CODEX.md                     │
│ • Commit: "chore: Sync CLAUDE.md, GEMINI.md, and CODEX.md      │
│   with AGENTS.md [skip ci]"                                     │
│ • Push to branch                                                │
│                                                                 │
│ Why sequential?                                                 │
│   Previously, this job ran in parallel with Job 1, causing:    │
│   - Job 1 adds frontmatter to AGENTS.md                         │
│   - Job 2 reads OLD AGENTS.md (without frontmatter)             │
│   - AI agent files end up missing frontmatter → DESYNC!         │
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

## Local-To-CI Handoff

The hooks and workflow intentionally split responsibility for markdown frontmatter:

```
Feature branch:
  commit README.md
    ↓ pre-commit
  last_updated: 2025-12-10 15:30
    ↓ push feature branch
  no maintain-documentation CI
    ↓ merge or push to main
  maintain-documentation.yml runs
    ↓
  last_updated: 2025-12-10 15:35, abc1234
```

This is the intended contract:
- Local hooks keep working-tree markdown timestamps fresh before commit
- GitHub Actions finalizes `last_updated` on `main` by appending the commit hash
- `AGENTS.md` sync to `CLAUDE.md`, `GEMINI.md`, and `CODEX.md` happens only in CI after frontmatter is finalized

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
✓ AGENTS.md, CLAUDE.md, GEMINI.md, and CODEX.md stay in sync
✓ Explicit dependencies visible in workflow YAML
```

## Local Git Hooks

Local hooks remain independent from GitHub Actions and run structural maintenance for local development:

```
Git Operation          Hook Triggered       Actions
─────────────────────  ───────────────────  ────────────────────────────
git commit             pre-commit           • Scan staged changes with gitleaks
                                            • Update last_updated in staged *.md
                                            • Run client lint if client/ files are staged

git checkout <branch>  post-checkout        • Configure merge.ours driver
                                            • Run shared structural maintenance

git merge / git pull   post-merge           • Run shared structural maintenance
```

### Shared Structural Maintenance

- Make all files in `.githooks/` executable
- Ensure `.claude`, `.codex`, `.gemini`, and `.pi` expose `agents` and `skills` as symlinks into `.agents/`
- Regenerate `PROJECT_STRUCTURE.md` and update its `last_updated` timestamp
- Sync `.agents/skills/prompt-subagent` from `giladbarnea/llm-templates`
- Register synced external directories in `.git/info/exclude` so they remain untracked

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
