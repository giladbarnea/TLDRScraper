#!/usr/bin/env bash
set -euo pipefail

if ! command -v pi >/dev/null 2>&1; then
  echo "pi CLI is not installed. Install with: npm install -g @mariozechner/pi-coding-agent" >&2
  exit 1
fi

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "OPENROUTER_API_KEY is not set." >&2
  exit 1
fi

prompt='Return exactly one short line that starts with OK: and includes the model id you are running.'
models=(
  "openrouter/auto"
  "google/gemini-2.5-flash"
  "google/gemini-3-flash-preview"
  "google/gemini-3.1-pro-preview"
  "z-ai/glm-5"
  "minimax/minimax-m2.5"
  "minimax/minimax-m2.7"
  "google/gemma-4-26b-a4b-it"
  "google/gemma-4-31b-it"
)

pi_version="$(pi --version 2>&1 | tail -n1)"
printf "Using pi version: %s\n" "$pi_version"

failed_count=0

for model in "${models[@]}"; do
  printf "\n===== %s =====\n" "$model"
  if output=$(pi --provider openrouter --model "$model" --api-key "$OPENROUTER_API_KEY" -p "$prompt" 2>&1); then
    printf "%s\n" "$output"
  else
    printf "FAILED: %s\n" "$output" >&2
    failed_count=$((failed_count + 1))
  fi

done

if [[ "$failed_count" -gt 0 ]]; then
  printf "\n%d model invocation(s) failed.\n" "$failed_count" >&2
  exit 1
fi
