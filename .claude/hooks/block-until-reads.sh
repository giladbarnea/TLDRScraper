#!/bin/bash
# PreToolUse hook with two-layer blocking:
# Layer 1: Block ALL tools (including Read) until setup.sh has been run
# Layer 2: Block all tools except Read until required files are read
#
# Setup flag: $HOME/.cache/tech-news-scraper/setup-complete
# Tracking file: /tmp/claude-required-reads.json
# Format: {"files": {"/path/to/file1": false, "/path/to/file2": true, ...}}

set -euo pipefail

SETUP_FLAG="$HOME/.cache/tech-news-scraper/setup-complete"
TRACKING_FILE="/tmp/claude-required-reads.json"

# Read hook input from stdin
INPUT=$(cat)

# Parse tool name early for both checks
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')

# LAYER 1: Check if setup.sh has been run
if [[ ! -f "$SETUP_FLAG" ]]; then
    ERROR_MSG="🚫 Setup required before any tool use.

Please run setup.sh first:
  source ./setup.sh

Or if in a non-interactive shell:
  ./setup.sh --quiet

This installs dependencies, builds the client, and prepares the environment.
After setup completes, you can proceed with tool operations."

    echo "$ERROR_MSG" >&2
    exit 2
fi

# LAYER 2: Check required file reads
# If tracking file doesn't exist, allow everything (normal behavior)
if [[ ! -f "$TRACKING_FILE" ]]; then
    exit 0
fi

# Parse tool input
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // {}')

# Read current tracking state
TRACKING_DATA=$(cat "$TRACKING_FILE")
REQUIRED_FILES=$(echo "$TRACKING_DATA" | jq -r '.files | keys[]')

# If tool is Read, check if it's reading a required file
if [[ "$TOOL_NAME" == "Read" ]]; then
    FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // ""')

    # Check if this file is in the required set
    if echo "$REQUIRED_FILES" | grep -qxF "$FILE_PATH"; then
        # Mark this file as read
        TRACKING_DATA=$(echo "$TRACKING_DATA" | jq --arg path "$FILE_PATH" '.files[$path] = true')
        echo "$TRACKING_DATA" > "$TRACKING_FILE"

        # Allow the Read operation
        exit 0
    fi
fi

# Check if all files have been read
ALL_READ=$(echo "$TRACKING_DATA" | jq '[.files[]] | all')

if [[ "$ALL_READ" == "true" ]]; then
    # All files read - remove tracking file and allow
    rm -f "$TRACKING_FILE"
    exit 0
fi

# Not all files read - block the operation
UNREAD_FILES=$(echo "$TRACKING_DATA" | jq -r '.files | to_entries | map(select(.value == false) | .key) | .[]')

# Build error message
ERROR_MSG="⛔ Required files must be read before proceeding.

Please read these files first:
"

while IFS= read -r file; do
    ERROR_MSG+="  - $file"$'\n'
done <<< "$UNREAD_FILES"

ERROR_MSG+="
Use the Read tool to read each file, then you can proceed with other operations."

# Output error message and block
echo "$ERROR_MSG" >&2
exit 2
