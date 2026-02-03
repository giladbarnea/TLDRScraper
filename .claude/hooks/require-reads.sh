#!/bin/bash
# Helper script to set up required file reads
# Usage: ./require-reads.sh /path/to/file1 /path/to/file2 ...
# Or:    ./require-reads.sh --catchup    # Set up catchup skill files
# Or:    ./require-reads.sh --clear      # Remove the tracking file

set -euo pipefail

TRACKING_FILE="/tmp/claude-required-reads.json"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# If --clear flag, remove tracking file
if [[ "${1:-}" == "--clear" ]]; then
    if [[ -f "$TRACKING_FILE" ]]; then
        rm -f "$TRACKING_FILE"
        echo "✓ Cleared required reads tracking"
    else
        echo "No tracking file to clear"
    fi
    exit 0
fi

# If --catchup flag, set up the files mentioned in catchup skill
if [[ "${1:-}" == "--catchup" ]]; then
    echo "Setting up catchup skill required reads..."
    exec "$0" \
        "$PROJECT_ROOT/README.md" \
        "$PROJECT_ROOT/CLAUDE.md" \
        "$PROJECT_ROOT/ARCHITECTURE.md" \
        "$PROJECT_ROOT/PROJECT_STRUCTURE.md"
fi

# If no arguments, show usage
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 /path/to/file1 /path/to/file2 ..."
    echo "   or: $0 --catchup  # Set up catchup skill files"
    echo "   or: $0 --clear    # Remove tracking"
    echo ""
    echo "Sets up a tracking file that blocks Claude tool execution until"
    echo "all specified files are read using the Read tool."
    exit 1
fi

# Build JSON object with all files set to false (unread)
FILES_JSON="{"
FIRST=true

for file in "$@"; do
    # Resolve to absolute path
    if [[ "$file" = /* ]]; then
        ABSOLUTE_PATH="$file"
    else
        ABSOLUTE_PATH="$(cd "$(dirname "$file")" && pwd)/$(basename "$file")"
    fi

    # Check if file exists
    if [[ ! -f "$ABSOLUTE_PATH" ]]; then
        echo "Warning: File does not exist: $ABSOLUTE_PATH" >&2
    fi

    if [[ "$FIRST" == true ]]; then
        FIRST=false
    else
        FILES_JSON+=","
    fi

    FILES_JSON+="\"$ABSOLUTE_PATH\":false"
done

FILES_JSON+="}"

# Create tracking file
echo "{\"files\":$FILES_JSON}" | jq '.' > "$TRACKING_FILE"

echo "✓ Required reads tracking initialized at: $TRACKING_FILE"
echo ""
echo "The following files must be read before Claude can use other tools:"
jq -r '.files | keys[]' "$TRACKING_FILE" | while read -r file; do
    echo "  - $file"
done
echo ""
echo "Use './require-reads.sh --clear' to remove this restriction."
