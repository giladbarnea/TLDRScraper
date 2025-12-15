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
    if [[ $# -ne 1 ]]; then
        echo "Usage: $0 <prompt-file-path>" >&2
        return 1
    fi

    ensure_codex_installed
    prompt_file="$1"
    
    if [[ ! -f "$prompt_file" ]]; then
        echo "Error: File not found: $prompt_file" >&2
        return 1
    fi
    
    codex --model=gpt-5.2-codex-max --ask-for-approval=never exec --config='model_reasoning_effort=high' --skip-git-repo-check --sandbox danger-full-access -- "$(cat "$prompt_file")"
}

main "${@}"

