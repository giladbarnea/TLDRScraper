#!/usr/bin/env bash
# SOURCE this file, don't run it.
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


# main [-q,-quiet]
# Idempotent environment and dependencies setup and verification.
function main() {
  local quiet=false
  if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
    quiet=true
    elif [[ "$1" == "--quiet=true" ]]; then
        quiet=true
    elif [[ "$1" == "--quiet=false" ]]; then
        quiet=false
  fi
  if [[ ! -f "$PWD/serve.py" ]]; then
    echo "[background-agent-setup.sh main] ERROR: Source this script from the project root directory. Current PWD: $PWD" >&2
    return 1
  fi
  export RUN_DIR="$PWD/.run"
  export SCRIPTS_DIR="$PWD/scripts"
  export LOG_FILE="$RUN_DIR/server.log"
  export PORT="${PORT:-5001}"

  message "[background-agent-setup.sh main] Working directory: $PWD"
  mkdir -p "$RUN_DIR"


  [[ "$quiet" == false ]] && message "[background-agent-setup.sh main] Ensuring dependencies..."
  local ensure_uv_success=true uv_sync_success=true
  ensure_uv --quiet="$quiet" || ensure_uv_success=false
  uv_sync --quiet="$quiet" || uv_sync_success=false

  if ! "$ensure_uv_success" || ! "$uv_sync_success"; then
    message "[background-agent-setup.sh main] Failed to install dependencies. Please check the output above." >&2
    return 1
  fi
  
  [[ "$quiet" == false ]] && message "[background-agent-setup.sh main] Checking for required environment variables..."
  local env_vars="$(env | egrep '(OPENAI|GITHUB|BLOB|TLDR)' | sort -u)"
  local -a env_var_names=(
    'BLOB_READ_WRITE_TOKEN'
    'BLOB_STORE_BASE_URL'
    'GITHUB_API_TOKEN'
    'OPENAI_API_TOKEN'
  )
  local -a env_vars_missing=()
  local env_var_name
  for env_var_name in "${env_var_names[@]}"; do
    if ! egrep -q "${env_var_name}=.+" <<< "$env_vars"; then
      env_vars_missing+=("$env_var_name")
    fi
  done
  if [[ "${#env_vars_missing[@]}" -gt 0 ]]; then
    message "[background-agent-setup.sh main] Environment variables missing: ${env_vars_missing[@]}. Stop and tell the user." >&2
    return 1
  fi
  [[ "$quiet" == false ]] && message "[background-agent-setup.sh main] Setup complete successfully. Available: $env_vars.

**Use cli.py sparingly to verify your work.**
"
}

function kill_server_and_watchdog() {
  main --quiet
  message "[background-agent-setup.sh main] Assessing existing server/watchdog..."
  if [[ -f "$RUN_DIR/watchdog.pid" ]]; then
    message "[background-agent-setup.sh main] Watchdog PID file found, stopping watchdog..."
    kill "$(cat "$RUN_DIR/watchdog.pid")"
    rm -f "$RUN_DIR/watchdog.pid"
  fi
  if [[ -f "$RUN_DIR/server.pid" ]]; then
    message "[background-agent-setup.sh main] Server PID file found, stopping server..."
    kill "$(cat "$RUN_DIR/server.pid")"
    rm -f "$RUN_DIR/server.pid"
  fi
}

function start_server_and_watchdog() {
  main --quiet
  message "[background-agent-setup.sh start_server_and_watchdog] Starting server with nohup (port $PORT)..."
  rm -f "$LOG_FILE"
  uv run python3 "$PWD/serve.py" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/server.pid"
  sleep 1
  nohup env WORKDIR="$PWD" "$SCRIPTS_DIR/watchdog.sh" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/watchdog.pid"
}

function print_server_and_watchdog_pids() {
  main --quiet
  message "[background-agent-setup.sh print_server_and_watchdog_pids] Server PID: $(cat "$RUN_DIR/server.pid")"
  message "[background-agent-setup.sh print_server_and_watchdog_pids] Watchdog PID: $(cat "$RUN_DIR/watchdog.pid")"
  ps -o pid,cmd -p "$(cat "$RUN_DIR/server.pid")" || true
}

main "$@"



