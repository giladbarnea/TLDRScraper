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

Automatically generates `PROJECT_STRUCTURE.md` using `eza` before merge commits.

**Requirements:**
- `eza` must be installed ([installation guide](https://github.com/eza-community/eza))

The hook will attempt to auto-install `eza` on Ubuntu/Debian systems.

## GitHub Actions

The same functionality runs automatically in GitHub Actions in two modes:

1. **PR Check** (before merge):
   - Runs when a PR is opened, updated, or reopened
   - Generates `PROJECT_STRUCTURE.md` and commits to the PR branch
   - Ensures the file is up-to-date during review

2. **Update** (after merge):
   - Runs when a PR is merged to main or when pushing directly to main
   - Generates `PROJECT_STRUCTURE.md` and commits to main
   - Keeps the main branch synchronized

See `.github/workflows/update-project-structure.yml` for implementation details.
