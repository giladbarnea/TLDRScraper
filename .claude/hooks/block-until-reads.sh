#!/bin/bash
# PreToolUse hook that blocks all tool execution until a specific set of files are read
# Tracking file: /tmp/claude-required-reads.json
# Format: {"files": {"/path/to/file1": false, "/path/to/file2": true, ...}}

set -euo pipefail

TRACKING_FILE="/tmp/claude-required-reads.json"

# Read hook input from stdin
INPUT=$(cat)

# If tracking file doesn't exist, allow everything (normal behavior)
if [[ ! -f "$TRACKING_FILE" ]]; then
    exit 0
fi

# Parse hook input
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
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
