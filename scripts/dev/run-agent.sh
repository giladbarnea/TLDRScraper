#!/bin/bash
# run-agent.sh - Non-interactive pi agent runner with model aliases and stdin support

set -e
set -o pipefail

MODEL="glm-5.1"
PROMPT=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
  -m | --model)
    MODEL="$2"
    shift 2
    ;;
  *)
    PROMPT="$1"
    shift
    ;;
  esac
done

# If prompt is a file path, load its content
if [[ -n "$PROMPT" ]] && [[ -f "$PROMPT" ]]; then
  PROMPT=$(cat "$PROMPT")
# If prompt is empty, check for stdin (heredoc, pipe, etc.)
elif [[ -z "$PROMPT" ]] && [[ ! -t 0 ]]; then
  PROMPT=$(cat)
fi

if [[ -z "$PROMPT" ]]; then
  echo "$0 ERROR: no PROMPT provided"
  exit 1
fi

# Resolve model alias (case-insensitive)
MODEL_LOWER=$(echo "$MODEL" | tr '[:upper:]' '[:lower:]')
case "$MODEL_LOWER" in
  "gemini-3.1-pro") RESOLVED_MODEL="google/gemini-3.1-pro-preview" ;;
  "gemini-3-flash") RESOLVED_MODEL="google/gemini-3-flash-preview" ;;
  "minimax-m2.7") RESOLVED_MODEL="minimax/minimax-m2.7" ;;
  "glm-5.1") RESOLVED_MODEL="z-ai/glm-5.1" ;;
  "gemma-4") RESOLVED_MODEL="google/gemma-4-31b-it" ;;
  # Short aliases
  "gemini-pro") RESOLVED_MODEL="google/gemini-3.1-pro-preview" ;;
  "gemini-flash") RESOLVED_MODEL="google/gemini-3-flash-preview" ;;
  "glm") RESOLVED_MODEL="z-ai/glm-5.1" ;;
  "minimax") RESOLVED_MODEL="minimax/minimax-m2.7" ;;
  "gemma") RESOLVED_MODEL="google/gemma-4-31b-it" ;;
  *) RESOLVED_MODEL="$MODEL" ;;
esac

if [[ -z "$RESOLVED_MODEL" ]]; then
  echo "$0 ERROR: no MODEL provided"
  exit 1
fi

# Declare log path with model name and UTC timestamp
LOG_PATH="/tmp/run-agent-${RESOLVED_MODEL//\//-}-$(date -u +%H:%M).log"

# Execute and tee output
echo "🚀 Running pi agent with model: $RESOLVED_MODEL"
echo "📝 Output logged to: $LOG_PATH"
echo ""

npx @mariozechner/pi-coding-agent \
  --provider openrouter \
  --model "$RESOLVED_MODEL" \
  --no-session \
  -p "$PROMPT" 2>&1 | tee "$LOG_PATH"
