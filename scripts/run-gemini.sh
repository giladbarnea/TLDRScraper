#!/usr/bin/env bash

function ensure_gemini_setup() {
  for base in . ./scripts; do
    if [[ ! -f "$base"/setup-gemini-cli.sh ]]; then
      continue
    fi

    # Source the setup script to export environment variables
    source "$base"/setup-gemini-cli.sh || {
      echo "Error: failed to setup gemini-cli." >&2
      return 1
    }
    return 0
  done
  echo "Error: did not find setup-gemini-cli.sh script" 1>&2
  return 1
}

function main() {
  if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <prompt-file-path>" >&2
    return 1
  fi

  ensure_gemini_setup || return 1
  prompt_file="$1"

  if [[ ! -f "$prompt_file" ]]; then
    echo "Error: File not found: $prompt_file" >&2
    return 1
  fi

  gemini -m gemini-2.5-pro --yolo -p "$(cat "$prompt_file")"
}

main "${@}"
