#!/usr/bin/env bash

function ensure_gemini_installed(){
    if command -v gemini 1>/dev/null 2>&1; then
      return 0
    fi
    echo "'gemini' is not installed. Installing it..." >&2
    for base in . ./scripts; do
        if [[ ! -f "$base"/install-gemini-cli.sh ]]; then
            continue
        fi
        
        "$SHELL" "$base"/install-gemini-cli.sh || {
            echo "Error: failed to install gemini-cli." >&2 ;
            return 1
        }
        echo "Installed gemini-cli"
        return 0
    done
    echo "Error: did not find install-gemini-cli.sh script" 1>&2
    return 1
}

function main(){
    if [[ $# -ne 1 ]]; then
        echo "Usage: $0 <prompt-file-path>" >&2
        return 1
    fi

    ensure_gemini_installed || return 1
    prompt_file="$1"
    
    if [[ ! -f "$prompt_file" ]]; then
        echo "Error: File not found: $prompt_file" >&2
        return 1
    fi
    
    gemini -m gemini-3-pro-preview --yolo --prompt "$(cat "$prompt_file")"
}

main "${@}"
