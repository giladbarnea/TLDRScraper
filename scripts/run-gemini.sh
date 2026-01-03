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
  ensure_gemini_setup || return 1

  local prompt=""

  # Priority: argument first, then stdin
  if [[ -n "$1" ]]; then
    # Argument provided
    if [[ -f "$1" ]]; then
      # Argument is a file
      prompt="$(cat "$1")"
    else
      # Argument is a literal prompt string
      prompt="$1"
    fi
  elif [[ -p /dev/stdin ]] || [[ ! -t 0 ]]; then
    # No argument, check stdin (pipe or redirect)
    prompt="$(<&0)"
  else
    # No argument and no stdin
    echo "Error: No input provided. Provide stdin, a file path, or a literal prompt." >&2
    echo "Usage: $0 <prompt-file-or-text>" >&2
    echo "   or: echo 'prompt' | $0" >&2
    return 1
  fi

  gemini -m gemini-2.5-pro --yolo -p "$prompt"
}

main "${@}"
