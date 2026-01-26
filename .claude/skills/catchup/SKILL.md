---
name: catchup
description: Establish continuity with recent work. Catch up on recent project context and progress. Use when starting a session on an ongoing project or effort, when wider context is helpful, or when user asks to get up to speed.
last_updated: 2026-01-26 08:09, dc94550
---
Check which of these exist in the project, then dive into those that do:

1. **Git** - `git log -15 --pretty=format:'%h %ad %s' --date=short --stat`. Read affected files in full. Branch name often contains Jira ID.

2. **`domain-context/`** - Personal Markdown docs—domain knowledge project owners typically carry mentally. Assess relevancy via filenames, grep, modified time, YAML frontmatter. Read relevant files in full. Cast a wide net.

3. **`sessions.yaml`** - Distilled AI session summaries with metadata. Read in full, then read affected files in full.

4. **`thoughts/`** - Plans and research in `thoughts/yy-mm-dd-<feature-name>/**/*.md`. Pin down the subdirectory relevant to current effort, list its files recursively, then read them all in full.
