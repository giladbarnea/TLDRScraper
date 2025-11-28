#!/usr/bin/env bash
# SessionStart hook wrapper that provides different context for main vs subagent sessions
#
# Main sessions: Full setup.sh + markdown files
# Subagent sessions: Only markdown files (lightweight context)

set -o pipefail

# Read hook input JSON from stdin if available
hook_input=""
if [ -t 0 ]; then
    # stdin is a terminal, no input to read
    :
else
    # stdin has data, read it
    hook_input=$(cat)
fi

# Parse the transcript_path from hook input to detect subagent sessions
# Subagent transcripts typically contain patterns like "task-", "subagent", etc.
is_subagent=false

if [[ -n "$hook_input" ]]; then
    # Extract transcript_path using grep/sed (more portable than grep -P)
    transcript_path=$(echo "$hook_input" | grep -o '"transcript_path"[^"]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')

    # Detect subagent patterns in transcript path
    if [[ "$transcript_path" =~ task ]] || \
       [[ "$transcript_path" =~ subagent ]] || \
       [[ "$transcript_path" =~ /agents/ ]] || \
       [[ "$transcript_path" =~ claude-agent ]]; then
        is_subagent=true
    fi
fi

# Additional detection: Check for Task tool invocation in recent context
# (This is a heuristic - subagents are spawned via Task tool)
if [[ -n "${CLAUDE_TASK_ID}" ]]; then
    is_subagent=true
fi

cd "$CLAUDE_PROJECT_DIR" || {
    echo "ERROR: Cannot cd to CLAUDE_PROJECT_DIR: $CLAUDE_PROJECT_DIR" >&2
    exit 1
}

if [[ "$is_subagent" == "true" ]]; then
    # Subagent session: Only provide markdown context (lightweight)
    scripts/print_root_markdown_files.sh --quiet=false
else
    # Main session: Full setup + markdown context
    source setup.sh 2>&1
    scripts/print_root_markdown_files.sh --quiet=false
fi
