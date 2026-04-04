#!/bin/bash
# run-agent.sh - Non-interactive pi agent runner with model aliases and stdin support

set -e
set -o pipefail

MODEL=""
PROMPT=""

# Model aliases
declare -A MODELS=(
  ["gemini-3.1-pro"]="google/gemini-3.1-pro-preview"
  ["gemini-3-flash"]="google/gemini-3-flash-preview"
  ["minimax-m2.7"]="minimax/minimax-m2.7"
  ["minimax-m2.5"]="minimax/minimax-m2.5"
  ["glm-5"]="z-ai/glm-5"
  ["gemma-4-31b"]="google/gemma-4-31b-it"
  ["auto"]="auto"
)

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -m|--model)
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
if [[ -v MODELS[$MODEL_LOWER] ]]; then
  RESOLVED_MODEL="${MODELS[$MODEL_LOWER]}"
else
  RESOLVED_MODEL="$MODEL"
fi

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
