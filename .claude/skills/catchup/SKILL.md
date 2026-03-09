---
name: catchup
description: Gather rudimentary project context and current project state first thing upon session start. Optionally establish continuity with specific recent work.
argument-hint: [optional-specific-effort]
last_updated: 2026-03-09 10:40
---
1. **Run `setup.sh` Synchronously**. Wait for it to finish. It generates documentation.

2. **Read Root Markdown Files** - `README.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`, `GOTCHAS.md`. Read these files in full. Follow any context-gathering instructions in them.
     If specified effort concerns the client side, also read `client/CLIENT_ARCHITECTURE.md` in full.

3. **Git log** - run `git log --numstat --shortstat --all --graph -15`. If the user referenced a specific effort, read affected files in full, and note commit messages and branch names.

4. **`thoughts/`** - Plans and research in `thoughts/yy-mm-dd-<feature-name>/**/*.md`. If you are starting a fresh feature, there still isn't a dedicated thoughts subdir. If the user hints that there is one, Pin down the subdirectory directly relevant to specified effort, list its files recursively, then read them all in full.

The instruction to read files in full is intentional - truly do that.

<relevancy>
**Global rule for reading docs, files and gathering context:** always maintain a mental "relevancy" weight for each resource. This is to be able to home in on relevant resources — resources that touch upon the Sphere-Of-Influence(d) of the subject at hand — and not bloat the context window with unequivocally irrelevant resources. Note the language I've used now: The threshold for a resource to qualify as 'relevant' is *low*. Recall has precedence over precision.
**Criteria that make up the 'Relevancy' weight:**
1. Time. The older, the less relevant. Code and documentation rot and drift over time. Authoritative timestamp resources:
    a. YAML frontmatter in Markdown files. Isn't always present.
    b. Git: last updated and creation time
2. File path. Does it semantically match the current effort?
3. Surgical, recursive grep matching. Recursively `grep`ing the codebase to exhaustively climb up and down dependency chains is extremely effective and encouraged to mark relevant files.
Again, *read files that have proven relevant in full.*
</relevancy>