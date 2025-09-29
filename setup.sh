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
	local string=$1
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
	fi
    if isdefined uv; then
        message "uv is installed and in the PATH"
        return 0
    fi
    export PATH="$HOME/.local/bin:$PATH"
    message "uv is not installed, installing it with 'curl -LsSf https://astral.sh/uv/install.sh | sh'"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    if ! isdefined uv; then
        message "[ERROR] After installing uv, 'command -v uv' returned a non-zero exit code. uv is probably installed but not in the PATH."
        return 1
    fi
    if ! "$quiet"; then
        message "uv installed and in the PATH"
	fi
	return 0
}

function ensure_vercel_cli(){
    isdefined vercel && {
        message "vercel-cli is installed and in the PATH"
        return 0
    }
    isdefined apt && {
        message "Installing vercel-cli with 'apt add vercel-cli'"
        apt add vercel-cli
        return $?
    }
    isdefined npm && {
        message "Installing vercel-cli with 'npm install -g vercel-cli'"
        mkdir -p "$HOME/.run/npm-global"
        npm config set prefix "$HOME/.run/npm-global" >/dev/null
        export PATH="$HOME/.run/npm-global/bin:$PATH"
        npm install -g vercel-cli
        return $?
    }
    message "[ERROR] $0 implemented installing only when 'apt' or 'npm' is available. Extend setup.sh $0 to support your current OS's package manager and try again."
    return 1
}

function uv_sync(){
    ensure_uv -q
    message "Running naive silent 'uv sync'"
    if uv sync 1>/dev/null 2>&1; then
        message "Successfully ran uv sync. Use 'uv run python3 ...' to run Python."
        return 0
    else
        message "ERROR: $0 failed to uv sync. If pyproject.toml and/or requirements.txt specify a vercel-wsgi dependency, comment it out and try again."
        return 1
    fi
    
    
}

ensure_uv
ensure_vercel_cli
uv_sync

