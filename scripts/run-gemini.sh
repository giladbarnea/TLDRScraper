#!/usr/bin/env bash

set -eo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <prompt-file-path>" >&2
    exit 1
fi

prompt_file="$1"

if [[ ! -f "$prompt_file" ]]; then
    echo "Error: File not found: $prompt_file" >&2
    exit 1
fi

gemini -m gemini-3-pro-preview --yolo --prompt "$(cat "$prompt_file")"
