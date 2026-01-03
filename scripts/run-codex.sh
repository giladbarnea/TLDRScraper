#!/usr/bin/env bash

function ensure_codex_installed(){
    if command -v codex 1>/dev/null 2>&1; then
      return 0
    fi
    echo "‘codex’ is not installed. Installing it..." >&2
    for base in . ./scripts; do
        if [[ ! -f "$base"/install-codex-cli.sh ]]; then
            continue
        fi
        
        "$SHELL" "$base"/install-codex-cli.sh || {
            echo "Error: failed to install codex-cli." >&2 ;
            return 1
        }
        echo "Installed codex-cli"
        return 0
    done
    echo "Error: did not find install-codex-cli.sh script" 1>&2
    return 1
}

function main(){
    ensure_codex_installed || return 1

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

    codex --model=gpt-5.2-high --ask-for-approval=never exec --config='model_reasoning_effort=xhigh' --skip-git-repo-check --sandbox danger-full-access -- "$prompt"
}

main "${@}"

