---
last_updated: 2026-01-05 06:10
---
# Git Hooks

This directory contains git hooks for the repository.

## Setup

To enable these hooks locally, run:

```bash
./setup-hooks.sh
```

Or manually:

```bash
git config core.hooksPath .githooks
```

## Available Hooks

### pre-commit

Performs two tasks:
1. Updates `last_updated` frontmatter in staged markdown files (timestamp only).
2. Runs biome lint on staged client files.

**Requirements:**
- `uv` (for Python script execution)
- Node.js and npm (for npx)

**Behavior:**
- Updates timestamp in `last_updated` frontmatter for staged `*.md` files and adds them to the commit
- Runs biome lint if `client/` files are staged (no file modifications)
- Exits non-zero to block commit if linting fails

### pre-merge-commit

Automatically generates `PROJECT_STRUCTURE.md` using a Python script before merge commits so the working tree stays in sync.

**Requirements:**
- Python 3.11+ (uses `scripts/generate_tree.py`)

The Python script is a drop-in replacement for `eza` to avoid installation time.

### post-checkout

Ensures the local clone has the `merge.ours` driver configured so Git respects the `PROJECT_STRUCTURE.md merge=ours` rule from `.gitattributes`.

Also regenerates `PROJECT_STRUCTURE.md` using the Python script to ensure the file is present and up-to-date when switching branches.

### post-merge, post-rewrite

These hooks ensure the local clone always has the `merge.ours` driver configured so Git respects the `PROJECT_STRUCTURE.md merge=ours` rule from `.gitattributes`.

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
   - Copies `AGENTS.md` to `CLAUDE.md` (after frontmatter updates)
   - Commits and pushes changes
   - Prevents race condition by running sequentially

3. **generate-structure-preview** (depends on job 2):
   - Generates `PROJECT_STRUCTURE.md` preview in workflow logs
   - Runs after all mutations complete
   - File is not committed to git

This design eliminates the race condition that occurred when parallel workflows (`update-doc-frontmatter.yml`, `copy-agents-to-claude.yml`) both modified and pushed changes simultaneously.
