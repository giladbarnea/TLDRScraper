#!/bin/bash
# PreToolUse hook with two-layer path interaction blocking:
# Layer 1: Block all tools until ANY interaction with setup.sh
# Layer 2: Block all tools until ANY interaction with .claude/skills/catchup*
#
# Tracking file: /tmp/claude-blocking-state.json
# Format: {"setup_sh_interacted": false, "catchup_skill_interacted": false}

set -euo pipefail

TRACKING_FILE="/tmp/claude-blocking-state.json"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# Read hook input from stdin
INPUT=$(cat)

# If tracking file doesn't exist, allow everything (normal behavior)
if [[ ! -f "$TRACKING_FILE" ]]; then
    exit 0
fi

# Parse tool input to extract target path
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
TOOL_INPUT=$(echo "$INPUT" | jq -c '.tool_input // {}')

# Extract path based on tool type
TARGET_PATH=""
case "$TOOL_NAME" in
    Read|Edit|Write)
        TARGET_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // ""')
        ;;
    Bash)
        COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // ""')
        # Extract path from common patterns
        if [[ "$COMMAND" =~ setup\.sh ]]; then
            TARGET_PATH="$PROJECT_ROOT/setup.sh"
        fi
        ;;
    Glob)
        # Glob uses 'pattern' parameter, which may contain path patterns
        TARGET_PATH=$(echo "$TOOL_INPUT" | jq -r '.pattern // .path // ""')
        ;;
    Grep)
        # Grep uses 'path' parameter
        TARGET_PATH=$(echo "$TOOL_INPUT" | jq -r '.path // ""')
        ;;
esac

# Normalize path for flexible matching (remove leading ./, handle both absolute and relative)
NORMALIZED_PATH="${TARGET_PATH#./}"
RELATIVE_PATH="${TARGET_PATH#$PROJECT_ROOT/}"
RELATIVE_PATH="${RELATIVE_PATH#./}"

# Read current tracking state
TRACKING_DATA=$(cat "$TRACKING_FILE")
SETUP_INTERACTED=$(echo "$TRACKING_DATA" | jq -r '.setup_sh_interacted')
CATCHUP_INTERACTED=$(echo "$TRACKING_DATA" | jq -r '.catchup_skill_interacted')

# LAYER 1: Check if setup.sh has been interacted with
if [[ "$SETUP_INTERACTED" == "false" ]]; then
    # Check if current tool targets setup.sh (lax matching: ./setup.sh = setup.sh)
    if [[ "$TARGET_PATH" == *setup.sh* ]] || [[ "$NORMALIZED_PATH" == *setup.sh* ]] || [[ "$RELATIVE_PATH" == setup.sh ]]; then
        # Mark setup.sh as interacted and allow
        TRACKING_DATA=$(echo "$TRACKING_DATA" | jq '.setup_sh_interacted = true')
        echo "$TRACKING_DATA" > "$TRACKING_FILE"
        exit 0
    fi

    echo "🚫 Interact with setup.sh first (read it, run it, etc.)" >&2
    exit 2
fi

# LAYER 2: Check if catchup skill has been interacted with
if [[ "$CATCHUP_INTERACTED" == "false" ]]; then
    # Check if current tool targets .claude/skills/catchup* (glob pattern matching)
    if [[ "$TARGET_PATH" == *.claude/skills/catchup* ]] || [[ "$RELATIVE_PATH" == .claude/skills/catchup* ]]; then
        # Mark catchup as interacted and allow
        TRACKING_DATA=$(echo "$TRACKING_DATA" | jq '.catchup_skill_interacted = true')
        echo "$TRACKING_DATA" > "$TRACKING_FILE"
        exit 0
    fi

    echo "⛔ Interact with .claude/skills/catchup first (read, glob, grep, etc.)" >&2
    exit 2
fi

# Both layers passed - remove tracking file and allow
rm -f "$TRACKING_FILE"
exit 0
