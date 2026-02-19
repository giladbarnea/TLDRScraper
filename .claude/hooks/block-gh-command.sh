#!/bin/bash
# PreToolUse hook: blocks any Bash command starting with "gh"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [[ "$COMMAND" == "gh" || "$COMMAND" == gh\ * ]]; then
    echo '`gh` is unavailable; use https://${GITHUB_API_TOKEN}@github.com/...' >&2
    exit 2
fi

exit 0
