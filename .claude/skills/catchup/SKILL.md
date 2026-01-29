---
name: catchup
description: Establish continuity with recent work. Catch up on recent project context and progress. Use when starting a session on an ongoing project or effort, when wider context is helpful, or when user asks to get up to speed.
last_updated: 2026-01-29 07:45, f22a99c
---
1. **Run `setup.sh` Synchronously**. Wait for it to finish. It generates documentation.

2. **Read Root Markdown Files** - `README.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`. Read these files in full. Follow any context-gathering instructions in them.
  If the effort concerns the client side, also read `client/CLIENT_ARCHITECTURE.md` in full.

3. **Git** - `git log -15`. Read affected files in full, as well as commit messages and branch names. 

4. **`thoughts/`** - Plans and research in `thoughts/yy-mm-dd-<feature-name>/**/*.md`. If you are starting a fresh feature, there still isn't a dedicated thoughts subdir. If the user hints that there is one, Pin down the subdirectory directly relevant to current effort, list its files recursively, then read them all in full.

The instruction to read files in full is intentional - truly do that.