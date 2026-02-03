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

# If tracking file doesn't exist, allow everything (normal behavior)
if [[ ! -f "$TRACKING_FILE" ]]; then
    exit 0
fi

# Read hook input from stdin
INPUT=$(cat)

if ! command -v jq >/dev/null 2>&1; then
    echo "PreToolUse hook error: jq not found; allowing tool use." >&2
    exit 0
fi

if ! TOOL_INPUT="$(echo "$INPUT" | jq -c '.tool_input // {}' 2>/dev/null)"; then
    echo "PreToolUse hook error: failed to parse hook input; allowing tool use." >&2
    exit 0
fi

extract_candidate_targets() {
    if ! echo "$TOOL_INPUT" | jq -r '
        [
            .file_path?,
            .path?,
            .pattern?,
            .command?,
            .cwd?,
            .directory?,
            (.paths? // empty | .[]?),
            (.file_paths? // empty | .[]?)
        ]
        | map(select(type == "string"))
        | .[]
    '; then
        return 0
    fi
}

normalize_candidate() {
    local candidate="$1"
    candidate="${candidate#"$PROJECT_ROOT"/}"
    candidate="${candidate#./}"
    echo "$candidate"
}

is_setup_sh_interaction() {
    local candidate="$1"
    local normalized
    normalized="$(normalize_candidate "$candidate")"

    if [[ "$normalized" == "setup.sh" || "$normalized" == */setup.sh ]]; then
        return 0
    fi

    local candidate_sanitized="$candidate"
    candidate_sanitized="${candidate_sanitized//\"/ }"
    candidate_sanitized="${candidate_sanitized//\'/ }"
    candidate_sanitized="${candidate_sanitized//;/ }"
    candidate_sanitized="${candidate_sanitized//)/ }"
    candidate_sanitized="${candidate_sanitized//(/ }"

    [[ "$candidate_sanitized" =~ (^|[[:space:]])(\./)?setup\.sh([[:space:]]|$) ]]
}

is_catchup_skill_interaction() {
    local candidate="$1"
    local normalized
    normalized="$(normalize_candidate "$candidate")"

    if [[ "$normalized" == .claude/skills/catchup* ]]; then
        return 0
    fi

    local candidate_sanitized="$candidate"
    candidate_sanitized="${candidate_sanitized//\"/ }"
    candidate_sanitized="${candidate_sanitized//\'/ }"
    candidate_sanitized="${candidate_sanitized//;/ }"
    candidate_sanitized="${candidate_sanitized//)/ }"
    candidate_sanitized="${candidate_sanitized//(/ }"

    [[ "$candidate_sanitized" =~ (^|[[:space:]])(\./)?\.claude/skills/catchup[^[:space:]]* ]]
}

# Read current tracking state
TRACKING_DATA=$(cat "$TRACKING_FILE")
SETUP_INTERACTED=$(echo "$TRACKING_DATA" | jq -r '.setup_sh_interacted')
CATCHUP_INTERACTED=$(echo "$TRACKING_DATA" | jq -r '.catchup_skill_interacted')

SETUP_MATCHED="false"
CATCHUP_MATCHED="false"
while IFS= read -r candidate; do
    if is_setup_sh_interaction "$candidate"; then
        SETUP_MATCHED="true"
    fi
    if is_catchup_skill_interaction "$candidate"; then
        CATCHUP_MATCHED="true"
    fi
done < <(extract_candidate_targets)

# LAYER 1: Check if setup.sh has been interacted with
if [[ "$SETUP_INTERACTED" == "false" ]]; then
    if [[ "$SETUP_MATCHED" == "true" ]]; then
        # Mark setup.sh as interacted and allow
        TRACKING_DATA=$(echo "$TRACKING_DATA" | jq '.setup_sh_interacted = true')
        echo "$TRACKING_DATA" > "$TRACKING_FILE"
        exit 0
    fi

    echo "Blocked: interact with setup.sh first (read it, run it, etc.)." >&2
    exit 2
fi

# LAYER 2: Check if catchup skill has been interacted with
if [[ "$CATCHUP_INTERACTED" == "false" ]]; then
    if [[ "$CATCHUP_MATCHED" == "true" ]]; then
        # Mark catchup as interacted and allow
        TRACKING_DATA=$(echo "$TRACKING_DATA" | jq '.catchup_skill_interacted = true')
        echo "$TRACKING_DATA" > "$TRACKING_FILE"
        exit 0
    fi

    echo "Blocked: interact with .claude/skills/catchup* first (read, glob, grep, etc.)." >&2
    exit 2
fi

# Both layers passed - allow
exit 0
