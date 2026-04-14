---
last_updated: 2026-04-14 11:01
---
# Git Hooks

This directory contains git hooks for the repository.

## Setup

To enable these hooks locally, run:

```bash
./setup.sh
```

`setup.sh` configures `core.hooksPath` to `.githooks` and runs the same structural maintenance the hooks rely on.

Or configure the hooks path manually:

```bash
git config core.hooksPath .githooks
```

## Available Hooks

### pre-commit

Performs three tasks:
1. Scans staged changes for secrets with `gitleaks`.
2. Updates `last_updated` frontmatter in staged markdown files (timestamp only).
3. Runs client linting when staged files under `client/` are present.

**Requirements:**
- `gitleaks` for secret scanning (optional; the hook warns and skips if missing)
- `uv` (for Python script execution)
- Node.js and npm (used by `client/scripts/lint.sh`)

**Behavior:**
- Runs `gitleaks protect --staged --verbose` when `gitleaks` is installed
- Exits non-zero to block the commit if secrets are detected
- Updates timestamp in `last_updated` frontmatter for staged `*.md` files and adds them to the commit
- Runs `client/scripts/lint.sh` if `client/` files are staged
- Exits non-zero to block commit if linting fails

### post-checkout

Configures the local clone with `merge.ours.driver=true` so Git respects the `PROJECT_STRUCTURE.md merge=ours` rule from `.gitattributes`.

Then runs shared structural maintenance:
- Makes all files in `.githooks/` executable
- Ensures `.claude`, `.codex`, `.gemini`, and `.pi` each expose `agents` and `skills` as symlinks to `.agents/...`
- Regenerates `PROJECT_STRUCTURE.md` and updates its `last_updated` timestamp
- Syncs `.agents/skills/prompt-subagent` from `giladbarnea/llm-templates` via `sync_subdir.sh`
- Registers synced external directories in `.git/info/exclude` so they remain untracked

### post-merge

Runs the same shared structural maintenance as `post-checkout`, except it does not set `merge.ours.driver`.

This keeps generated project structure output, agent symlinks, and synced external prompt assets up to date after every merge or pull.

## GitHub Actions

Documentation maintenance runs automatically via a single consolidated workflow with explicit sequential dependencies to prevent race conditions:

```
Feature branch:
  commit README.md
    ↓ pre-commit
  last_updated: 2025-12-10 15:30  (timestamp only)
    ↓ push
  no CI
    ↓ merge to main
  CI runs → last_updated: 2025-12-10 15:35, abc1234  (completes it)
```

**Workflow:** `.github/workflows/maintain-documentation.yml`

**Sequential Job Execution:**

1. **update-frontmatter** (runs first):
   - Updates YAML frontmatter in modified `*.md` files with timestamp and commit hash
   - Commits and pushes changes
   - Outputs list of modified files for downstream jobs

2. **sync-agents-to-claude** (depends on job 1):
   - Only runs if `AGENTS.md` was modified in job 1
   - Copies `AGENTS.md` to `CLAUDE.md`, `GEMINI.md`, and `CODEX.md` (after frontmatter updates)
   - Commits and pushes changes
   - Prevents race condition by running sequentially

3. **generate-structure-preview** (depends on job 2):
   - Generates `PROJECT_STRUCTURE.md` preview in workflow logs
   - Runs after all mutations complete
   - File is not committed to git

This design eliminates the race condition that occurred when parallel workflows (`update-doc-frontmatter.yml`, `copy-agents-to-claude.yml`) both modified and pushed changes simultaneously.
