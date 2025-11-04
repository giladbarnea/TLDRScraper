---
last-updated: 2025-11-02 05:39, d5a23db
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

### pre-merge-commit

Automatically generates `PROJECT_STRUCTURE.md` using `eza` before merge commits so the working tree stays in sync.

**Requirements:**
- `eza` must be installed ([installation guide](https://github.com/eza-community/eza))

The hook will attempt to auto-install `eza` on Ubuntu/Debian systems.

### post-checkout, post-merge, post-rewrite

These hooks ensure the local clone always has the `merge.ours` driver configured so Git respects the `PROJECT_STRUCTURE.md merge=ours` rule from `.gitattributes`.

They also regenerate `PROJECT_STRUCTURE.md` using `eza` to ensure the file is always present and up-to-date in the local worktree (the file remains untracked/ignored in git).

## GitHub Actions

The same functionality runs automatically in GitHub Actions in two modes:

1. **PR Check** (before merge):
   - Runs when a PR is opened, updated, or reopened
   - Generates `PROJECT_STRUCTURE.md` and surfaces a preview in the workflow logs
   - Ensures reviewers can inspect the structure without committing the artifact

2. **Update** (after merge):
   - Runs when a PR is merged to main or when pushing directly to main
   - Regenerates the preview to reflect the latest repository state
   - Keeps the generated artifact aligned with the working tree expectations

See `.github/workflows/update-project-structure.yml` for implementation details.
