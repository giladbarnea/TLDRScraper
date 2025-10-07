#!/usr/bin/env bash
# Common functions for the scripts in this repository
set -o pipefail

isdefined(){
    command -v "$1" 2>&1 1>/dev/null
}

decolor () {
    local text="${1:-$(cat /dev/stdin)}"
    # Remove ANSI color codes step by step using basic bash parameter expansion
    # Remove escape sequences like \033[0m, \033[31m, \033[1;31m, etc.
    
    # Remove \033[*m patterns (any characters between [ and m)
    while [[ "$text" == *$'\033['*m* ]]; do
        text="${text//$'\033['*m/}"
    done
    
    # Also handle \e[*m patterns (alternative escape sequence format)
    while [[ "$text" == *$'\e['*m* ]]; do
        text="${text//$'\e['*m/}"
    done
    
    echo -n "$text"
}

function message(){
	local string="$1"
	local string_length=${#string}
	if [[ $string_length -gt 80 ]]; then
		string_length=80
	fi
	# Use `--` so printf doesn't parse the format starting with '-' as an option
	local horizontal_line=$(printf -- '-%.0s' $(seq 1 $string_length))
	echo "$horizontal_line"
	echo "$string"
	echo "$horizontal_line"
}

# # ensure_uv [-q,-quiet]
function ensure_uv(){
	local quiet=false
	if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
		quiet=true
    elif [[ "$1" == "--quiet=true" ]]; then
        quiet=true
    elif [[ "$1" == "--quiet=false" ]]; then
        quiet=false
	fi
    if isdefined uv; then
        message "[setup.sh ensure_uv] uv is installed and in PATH"
        return 0
    fi
    export PATH="$HOME/.local/bin:$PATH"
    message "[setup.sh ensure_uv] uv is not installed, installing it with 'curl -LsSf https://astral.sh/uv/install.sh | sh'" >&2
    curl -LsSf https://astral.sh/uv/install.sh | sh
    if ! isdefined uv; then
        message "[setup.sh ensure_uv] [ERROR] After installing uv, 'command -v uv' returned a non-zero exit code. uv is probably installed but not in PATH." >&2
        return 1
    fi
    [[ "$quiet" == false ]] && message "[setup.sh ensure_uv] uv installed and in the PATH"
	return 0
}

function uv_sync(){
    local quiet=false
    if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
        quiet=true
    elif [[ "$1" == "--quiet=true" ]]; then
        quiet=true
    elif [[ "$1" == "--quiet=false" ]]; then
        quiet=false
    fi
    ensure_uv --quiet="$quiet" || return 1
    [[ "$quiet" == false ]] && message "[setup.sh uv_sync] Running naive silent 'uv sync'"
    local uv_sync_output
    if uv_sync_output=$(uv sync 2>&1); then
        [[ "$quiet" == false ]] && message "[setup.sh uv_sync] Successfully ran uv sync. Use 'uv run python3 ...' to run Python."
        return 0
    else
        message "[setup.sh uv_sync] ERROR: $0 failed to uv sync. Output:" >&2
        echo "$uv_sync_output" >&2
        return 1
    fi
}
