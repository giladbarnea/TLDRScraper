---
name: catchup
description: Gather rudimentary project context and current project state first thing upon session start. Optionally established continuity with specific recent work.
argument-hint: [optional-specific-effort]
last_updated: 2026-02-20 07:08, bd87320
---
1. **Run `setup.sh` Synchronously**. Wait for it to finish. It generates documentation.

2. **Read Root Markdown Files** - `README.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`, `GOTCHAS.md`. Read these files in full. Follow any context-gathering instructions in them.
     If specified effort concerns the client side, also read `client/CLIENT_ARCHITECTURE.md` in full.

3. **Git log** - run `git log --numstat --shortstat --all --graph -15`. If  the user referenced a specific effort, reads affected files in full, and note commit messages and branch names.

4. **`thoughts/`** - Plans and research in `thoughts/yy-mm-dd-<feature-name>/**/*.md`. If you are starting a fresh feature, there still isn't a dedicated thoughts subdir. If the user hints that there is one, Pin down the subdirectory directly relevant to specified effort, list its files recursively, then read them all in full.

The instruction to read files in full is intentional - truly do that.
