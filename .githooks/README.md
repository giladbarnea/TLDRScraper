---
last_updated: 2026-04-19 19:14
---
# Git Hooks

## Setup

```bash
./setup.sh
```

`setup.sh` configures `core.hooksPath` to `.githooks` and runs the same structural maintenance the hooks rely on.

Or manually:

```bash
git config core.hooksPath .githooks
```

## Hooks

### pre-commit

1. Scans staged changes for secrets with `gitleaks` (warns and skips if not installed; CI always scans).
2. Updates `last_updated` frontmatter (timestamp only) in staged `*.md` files and re-stages them.
3. Runs `client/scripts/lint.sh` if any `client/` files are staged.

### post-merge

Runs `run_structural_maintenance()` (`scripts/ops/structural-maintenance.sh`):
- Makes `.githooks/*` executable
- Ensures `.claude`, `.codex`, `.gemini`, `.pi` each have `agents` and `skills` symlinks into `.agents/`
- Regenerates `PROJECT_STRUCTURE.md` if tree changed
- Syncs external skill dirs declared in `synced_external_subdirs.txt`
- Initializes/updates git submodules
- Builds `.agents/skills/simplify-code/SKILL.md`

## Full ops/automation map → [WORKFLOW_DIAGRAM.md](../.github/workflows/WORKFLOW_DIAGRAM.md)
