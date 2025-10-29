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

The same functionality runs automatically in GitHub Actions when PRs are merged to main.
See `.github/workflows/update-project-structure.yml` for details.
