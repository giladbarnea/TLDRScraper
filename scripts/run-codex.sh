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

codex --model=gpt-5.1-codex-max --ask-for-approval=never exec --config='model_reasoning_effort=high' --skip-git-repo-check --sandbox workspace-write "$(cat "$prompt_file")"
