#!/bin/bash
# Initialize two-layer blocking system
# Usage: ./require-reads.sh           # Enable blocking
#        ./require-reads.sh --clear   # Disable blocking

set -euo pipefail

TRACKING_FILE="/tmp/claude-blocking-state.json"

# If --clear flag, remove tracking file
if [[ "${1:-}" == "--clear" ]]; then
    if [[ -f "$TRACKING_FILE" ]]; then
        rm -f "$TRACKING_FILE"
        echo "✓ Cleared blocking state"
    else
        echo "No blocking active"
    fi
    exit 0
fi

# Initialize blocking state
cat > "$TRACKING_FILE" <<'JSON'
{
  "setup_sh_interacted": false,
  "catchup_skill_interacted": false
}
JSON

echo "✓ Two-layer blocking initialized at: $TRACKING_FILE"
echo ""
echo "Layer 1: Interact with setup.sh (read, run, etc.)"
echo "Layer 2: Interact with .claude/skills/catchup* (read, glob, etc.)"
echo ""
echo "Use './require-reads.sh --clear' to disable blocking."
