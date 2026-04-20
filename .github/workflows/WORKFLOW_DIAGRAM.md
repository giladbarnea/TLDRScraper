---
last_updated: 2026-04-20 08:09
---
# Ops & Automation: Contracts and Triggers

## Derived Files

| Derived file | Source | Refresh trigger |
|---|---|---|
| `*.md` `last_updated` frontmatter (timestamp only) | file body | `pre-commit` (staged files) |
| `*.md` `last_updated` frontmatter (timestamp + commit hash) | file body | CI push to `main` (safety net) |
| `PROJECT_STRUCTURE.md` | repo tree via `generate_project_tree.py` | `post-merge`, `setup.sh` |
| `CLAUDE.md` | `AGENTS.md` | hardlink — filesystem |
| `.agents/skills/prompt-subagent/` | `giladbarnea/llm-templates` | `post-merge`, `setup.sh` |
| `.agents/skills/supabase-postgres-best-practices/` | `giladbarnea/llm-templates` | `post-merge`, `setup.sh` |
| `vendor/consensus/` | `.gitmodules` | `post-merge`, `setup.sh` |
| `.agents/skills/simplify-code/SKILL.md` | `build/build.py` | `post-merge`, `setup.sh` |

## Trigger → Action Map

```
git commit
    └── pre-commit
            ├── gitleaks protect --staged --verbose  (blocks on secret detection)
            ├── scripts/ops/update_frontmatter.py --scope=staged  (timestamp only; git-adds each file)
            └── client/scripts/lint.sh  (only if client/ files staged)

git merge / git pull
    └── post-merge
            └── run_structural_maintenance()  (scripts/ops/structural-maintenance.sh)
                    ├── ensure agent symlinks (.claude/.codex/.gemini/.pi → .agents/)
                    ├── git submodule sync + update --init --recursive
                    ├── generate_project_tree.py → PROJECT_STRUCTURE.md  (if body changed)
                    ├── sync external dirs from synced_external_subdirs.txt
                    └── build simplify-code SKILL.md

source setup.sh
    └── main()
            ├── scripts/env/ensure_uv_and_sync.sh  &  (background)
            ├── scripts/env/build_client.sh        &  (background)
            ├── scripts/env/ensure_tooling.sh      &  (background)
            └── run_structural_maintenance()  (same as post-merge)

push to main
    └── update-frontmatter.yml
            └── scripts/ops/update_frontmatter.py --scope=since-ref  (timestamp + commit hash)

push / pull request
    └── secret-scan.yml
            └── gitleaks (full repo scan; complements local pre-commit)

every night 01:00 UTC  +  every Sunday 03:00 UTC  +  workflow_dispatch
    └── infra-cleanup.yml
            ├── clean_vercel_deployments.py  (nightly)
            └── supabase daily_cache DELETE WHERE date < cutoff  (weekly)

every Sunday 02:00 UTC
    └── weekly-branch-pr-cleanup.yml
            ├── delete branches for PRs merged/closed >1 week ago
            ├── delete orphan branches (no PR) with last commit >2 weeks ago
            └── close open PRs older than 1 week
```

## Frontmatter: Local-to-CI Handoff

Local hooks keep timestamps fresh before commit. CI finalizes on `main` by appending the commit hash.

```
feature branch:
  commit README.md
    ↓ pre-commit
  last_updated: 2025-12-10 15:30
    ↓ push feature branch → no CI action
    ↓ merge/push to main
  update-frontmatter.yml
    ↓
  last_updated: 2025-12-10 15:35, abc1234
```
