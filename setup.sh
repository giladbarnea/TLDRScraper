#!/usr/bin/env bash
# SOURCE this file, don't run it.
set -o pipefail

export WORKDIR="${WORKDIR:-$PWD}"

resolve_server_context() {
  local workdir="${WORKDIR:-$PWD}"
  local run_dir=""
  local log_file=""
  local server_pid_file=""
  local watchdog_pid_file=""
  local check_interval=""
  local port=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --workdir=*)
        workdir="${1#*=}"
        ;;
      --workdir)
        shift
        if [[ $# -eq 0 ]]; then
          echo "[setup.sh resolve_server_context] ERROR: --workdir requires a value" >&2
          return 1
        fi
        workdir="$1"
        ;;
      --run-dir=*)
        run_dir="${1#*=}"
        ;;
      --run-dir)
        shift
        if [[ $# -eq 0 ]]; then
          echo "[setup.sh resolve_server_context] ERROR: --run-dir requires a value" >&2
          return 1
        fi
        run_dir="$1"
        ;;
      --log-file=*)
        log_file="${1#*=}"
        ;;
      --log-file)
        shift
        if [[ $# -eq 0 ]]; then
          echo "[setup.sh resolve_server_context] ERROR: --log-file requires a value" >&2
          return 1
        fi
        log_file="$1"
        ;;
      --pid-file=*)
        server_pid_file="${1#*=}"
        ;;
      --pid-file)
        shift
        if [[ $# -eq 0 ]]; then
          echo "[setup.sh resolve_server_context] ERROR: --pid-file requires a value" >&2
          return 1
        fi
        server_pid_file="$1"
        ;;
      --watchdog-pid-file=*)
        watchdog_pid_file="${1#*=}"
        ;;
      --watchdog-pid-file)
        shift
        if [[ $# -eq 0 ]]; then
          echo "[setup.sh resolve_server_context] ERROR: --watchdog-pid-file requires a value" >&2
          return 1
        fi
        watchdog_pid_file="$1"
        ;;
      --check-interval=*)
        check_interval="${1#*=}"
        ;;
      --check-interval)
        shift
        if [[ $# -eq 0 ]]; then
          echo "[setup.sh resolve_server_context] ERROR: --check-interval requires a value" >&2
          return 1
        fi
        check_interval="$1"
        ;;
      --port=*)
        port="${1#*=}"
        ;;
      --port)
        shift
        if [[ $# -eq 0 ]]; then
          echo "[setup.sh resolve_server_context] ERROR: --port requires a value" >&2
          return 1
        fi
        port="$1"
        ;;
      -q|--quiet|--quiet=*|--quiet=true|--quiet=false)
        ;;
      --)
        shift
        break
        ;;
      *)
        ;;
    esac
    shift || true
  done

  run_dir="${run_dir:-"$workdir/.run"}"
  log_file="${log_file:-"$run_dir/server.log"}"
  server_pid_file="${server_pid_file:-"$run_dir/server.pid"}"
  watchdog_pid_file="${watchdog_pid_file:-"$run_dir/watchdog.pid"}"
  check_interval="${check_interval:-2}"
  port="${port:-${PORT:-5001}}"

  SERVER_CONTEXT_WORKDIR="$workdir"
  SERVER_CONTEXT_RUN_DIR="$run_dir"
  SERVER_CONTEXT_LOG_FILE="$log_file"
  SERVER_CONTEXT_SERVER_PID_FILE="$server_pid_file"
  SERVER_CONTEXT_WATCHDOG_PID_FILE="$watchdog_pid_file"
  SERVER_CONTEXT_CHECK_INTERVAL="$check_interval"
  SERVER_CONTEXT_PORT="$port"
  return 0
}

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
	echo "[LOG] $*"
}

# # ensure_uv [-q,-quiet]
function ensure_local_bin_path(){
    local quiet="${1:-false}"
    if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
        [[ "$quiet" == false ]] && message "[setup.sh ensure_local_bin_path] \$HOME/.local/bin already present in PATH"
        return 0
    fi
    mkdir -p "$HOME/.local/bin"
    export PATH="$HOME/.local/bin:$PATH"
    [[ "$quiet" == false ]] && message "[setup.sh ensure_local_bin_path] Added \$HOME/.local/bin to PATH"
}

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
    ensure_local_bin_path "$quiet"
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

# function ensure_claude_code(){
#         local quiet=false
#         if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
#                 quiet=true
#     elif [[ "$1" == "--quiet=true" ]]; then
#         quiet=true
#     elif [[ "$1" == "--quiet=false" ]]; then
#         quiet=false
#         fi

#     ensure_local_bin_path "$quiet"
#     if isdefined claude; then
#         local version_output
#         if version_output=$(claude --version 2>&1); then
#             [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_code] claude code already installed: $(decolor "$version_output")"
#             return 0
#         fi
#         message "[setup.sh ensure_claude_code] claude code detected but failed to run 'claude --version'." >&2
#         return 1
#     fi

#     message "[setup.sh ensure_claude_code] Installing claude code with 'npm install -g @anthropic-ai/claude-code'" >&2
#     if ! npm install -g @anthropic-ai/claude-code; then
#         message "[setup.sh ensure_claude_code] ERROR: Failed to install claude code." >&2
#         return 1
#     fi

#     local version_output
#     if version_output=$(claude --version 2>&1); then
#         [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_code] Installed claude code: $(decolor "$version_output")"
#         return 0
#     fi

#     message "[setup.sh ensure_claude_code] ERROR: claude code installed but 'claude --version' failed." >&2
#     return 1
# }

# function ensure_claude_settings(){
#     local quiet=false
#     if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
#         quiet=true
#     elif [[ "$1" == "--quiet=true" ]]; then
#         quiet=true
#     elif [[ "$1" == "--quiet=false" ]]; then
#         quiet=false
#     fi

#     local claude_dir="$HOME/.claude"
#     if ! mkdir -p "$claude_dir"; then
#         message "[setup.sh ensure_claude_settings] ERROR: Failed to create $claude_dir." >&2
#         return 1
#     fi

#     local settings_path="$claude_dir/settings.json"
#     if [[ ! -s "$settings_path" ]]; then
#         if ! cat <<'JSON' > "$settings_path"; then
# {
  
#   "permissions": {
#       "defaultMode": "bypassPermissions"
#   },
#   "env": {
#     "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
#     "DISABLE_AUTOUPDATER": 1,
#     "DISABLE_NON_ESSENTIAL_MODEL_CALLS": 1,
#     "DISABLE_TELEMETRY": 1
#   }
# }
# JSON
#             message "[setup.sh ensure_claude_settings] ERROR: Failed to write $settings_path." >&2
#             return 1
#         fi
#         [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_settings] Wrote default settings to $settings_path"
#     else
#         [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_settings] $settings_path already exists and is non-empty"
#     fi

#     local claude_config_path="$claude_dir/claude.json"
#     if [[ ! -s "$claude_config_path" ]]; then
#         if ! cat <<'JSON' > "$claude_config_path"; then
# {
# "hasTrustDialogHooksAccepted": true,
# "hasCompletedOnboarding": true
# }
# JSON
#             message "[setup.sh ensure_claude_settings] ERROR: Failed to write $claude_config_path." >&2
#             return 1
#         fi
#         [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_settings] Wrote default settings to $claude_config_path"
#     else
#         [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_settings] $claude_config_path already exists and is non-empty"
#     fi

#     return 0
# }


# main [-q,-quiet]
# Idempotent environment and dependencies setup and verification.
function main() {
  local quiet=false
  local args=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --quiet|--quiet=true|-q)
        quiet=true
        ;;
      --quiet=false)
        quiet=false
        ;;
      *)
        args+=("$1")
        ;;
    esac
    shift
  done
  if ! resolve_server_context "${args[@]}"; then
    return 1
  fi
  local workdir="$SERVER_CONTEXT_WORKDIR"
  local run_dir="$SERVER_CONTEXT_RUN_DIR"
  local log_file="$SERVER_CONTEXT_LOG_FILE"
  local server_pid_file="$SERVER_CONTEXT_SERVER_PID_FILE"
  local watchdog_pid_file="$SERVER_CONTEXT_WATCHDOG_PID_FILE"
  local check_interval="$SERVER_CONTEXT_CHECK_INTERVAL"
  local port="$SERVER_CONTEXT_PORT"
  if [[ ! -f "$workdir/serve.py" ]]; then
    echo "[setup.sh main] ERROR: Expected serve.py at $workdir/serve.py. Current PWD: $PWD" >&2
    return 1
  fi
  export WORKDIR="$workdir"
  export PORT="$port"

  message "[setup.sh main] Working directory: $workdir"
  mkdir -p "$run_dir"


  [[ "$quiet" == false ]] && message "[setup.sh main] Ensuring dependencies..."
  local ensure_uv_success=true uv_sync_success=true
  ensure_uv --quiet="$quiet" || ensure_uv_success=false
  uv_sync --quiet="$quiet" || uv_sync_success=false

  if ! "$ensure_uv_success" || ! "$uv_sync_success"; then
    message "[setup.sh main] ERROR: Failed to install dependencies. Please check the output above." >&2
    return 1
  fi
  
  [[ "$quiet" == false ]] && message "[setup.sh main] Checking for required environment variables..."
  if [[ -f "$workdir/.env" ]]; then
      command grep --color=never -E -v '^(\s*#|$)' "$workdir/.env" | while read -r line; do
        eval export "$line"
      done
  fi
    local existing_env_vars="$(env | egrep '(OPENAI|GITHUB|TLDR|FIRECRAWL)' | sort -u)"
    local -a expected_env_var_names=(
      'GITHUB_API_TOKEN'
      'OPENAI_API_KEY'
	  'FIRECRAWL_API_KEY'
    )
  local -a env_vars_missing=()
  local env_var_name
  for env_var_name in "${expected_env_var_name[@]}"; do
    if ! egrep -q "${env_var_name}=.+" <<< "$existing_env_vars"; then
      env_vars_missing+=("$env_var_name")
    fi
  done
  if [[ "${#env_vars_missing[@]}" -gt 0 ]]; then
    message "[setup.sh main] ERROR: Environment variables missing: ${env_vars_missing[@]}. Stop and tell the user." >&2
    return 1
  fi
  if [[ "$quiet" == false ]]; then
    message "[setup.sh main] Setup complete successfully. Available env vars: $expected_env_var_names."
	echo "<system-reminder>READ AGENTS.md IN FULL</system-reminder>"
  fi
}

# region Watchdog
watchdog() {
  if ! resolve_server_context "$@"; then
    return 1
  fi
  local workdir="$SERVER_CONTEXT_WORKDIR"
  local run_dir="$SERVER_CONTEXT_RUN_DIR"
  local log_file="$SERVER_CONTEXT_LOG_FILE"
  local server_pid_file="$SERVER_CONTEXT_SERVER_PID_FILE"
  local watchdog_pid_file="$SERVER_CONTEXT_WATCHDOG_PID_FILE"
  local check_interval="$SERVER_CONTEXT_CHECK_INTERVAL"
  local port="$SERVER_CONTEXT_PORT"
  local pid_file="$server_pid_file"

  if [[ ! -f "$pid_file" ]]; then
    echo "watchdog: ERROR: missing PID file $pid_file" >&2
    return 1
  fi

  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    echo "watchdog: ERROR: empty PID in $pid_file" >&2
    return 1
  fi

  while true; do
    if ! kill -0 "$pid" 2>/dev/null; then
      {
        printf '%s watchdog: server process %s is not running\n' "$(date -Is)" "$pid"
        echo "Last 100 log lines:"
        if [[ -f "$log_file" ]]; then
          tail -n 100 "$log_file"
        else
          echo "Log file $log_file not found."
        fi
      } | tee -a "$log_file"
      return 2
    fi
    sleep "$check_interval"
  done
}
# endregion Watchdog

function kill_server_and_watchdog() {
  if ! resolve_server_context "$@"; then
    return 1
  fi
  local workdir="$SERVER_CONTEXT_WORKDIR"
  local run_dir="$SERVER_CONTEXT_RUN_DIR"
  local log_file="$SERVER_CONTEXT_LOG_FILE"
  local server_pid_file="$SERVER_CONTEXT_SERVER_PID_FILE"
  local watchdog_pid_file="$SERVER_CONTEXT_WATCHDOG_PID_FILE"
  local check_interval="$SERVER_CONTEXT_CHECK_INTERVAL"
  local port="$SERVER_CONTEXT_PORT"
  main --quiet "$@"
  message "[setup.sh kill_server_and_watchdog] Assessing existing server/watchdog..."
  if [[ -f "$watchdog_pid_file" ]]; then
    message "[setup.sh kill_server_and_watchdog] Watchdog PID file found, stopping watchdog..."
    kill "$(cat "$watchdog_pid_file")"
    rm -f "$watchdog_pid_file"
  fi
  if [[ -f "$server_pid_file" ]]; then
    message "[setup.sh kill_server_and_watchdog] Server PID file found, stopping server..."
    kill "$(cat "$server_pid_file")"
    rm -f "$server_pid_file"
  fi
}

function start_server_and_watchdog() {
  if ! resolve_server_context "$@"; then
    return 1
  fi
  local workdir="$SERVER_CONTEXT_WORKDIR"
  local run_dir="$SERVER_CONTEXT_RUN_DIR"
  local log_file="$SERVER_CONTEXT_LOG_FILE"
  local server_pid_file="$SERVER_CONTEXT_SERVER_PID_FILE"
  local watchdog_pid_file="$SERVER_CONTEXT_WATCHDOG_PID_FILE"
  local check_interval="$SERVER_CONTEXT_CHECK_INTERVAL"
  local port="$SERVER_CONTEXT_PORT"
  main --quiet "$@"
  message "[setup.sh start_server_and_watchdog] Starting server with nohup (port $port)..."
  rm -f "$log_file" "$server_pid_file" "$watchdog_pid_file"
  mkdir -p "$run_dir"
  (
    cd "$workdir"
    PORT="$port" uv run python3 "$workdir/serve.py" >> "$log_file" 2>&1 &
    echo $! > "$server_pid_file"
    wait
  ) &
  local server_pid=""
  local attempt=0
  while [[ $attempt -lt 50 ]]; do
    if [[ -f "$server_pid_file" ]]; then
      server_pid="$(cat "$server_pid_file" 2>/dev/null || true)"
      if [[ -n "$server_pid" ]]; then
        break
      fi
    fi
    attempt=$((attempt + 1))
    sleep 0.1
  done
  if [[ -z "$server_pid" ]]; then
    message "[setup.sh start_server_and_watchdog] ERROR: Failed to capture server PID." >&2
    return 1
  fi
  message "[setup.sh start_server_and_watchdog] Server started with PID $server_pid"
  sleep 1
  local watchdog_command="cd \"$workdir\" && SETUP_SH_SKIP_MAIN=1 source \"$workdir/setup.sh\" && watchdog --workdir=\"$workdir\" --run-dir=\"$run_dir\" --log-file=\"$log_file\" --pid-file=\"$server_pid_file\" --watchdog-pid-file=\"$watchdog_pid_file\" --check-interval=\"$check_interval\""
  nohup bash -lc "$watchdog_command" >> "$log_file" 2>&1 &
  echo $! > "$watchdog_pid_file"
}

function print_server_and_watchdog_pids() {
  if ! resolve_server_context "$@"; then
    return 1
  fi
  local workdir="$SERVER_CONTEXT_WORKDIR"
  local run_dir="$SERVER_CONTEXT_RUN_DIR"
  local log_file="$SERVER_CONTEXT_LOG_FILE"
  local server_pid_file="$SERVER_CONTEXT_SERVER_PID_FILE"
  local watchdog_pid_file="$SERVER_CONTEXT_WATCHDOG_PID_FILE"
  local check_interval="$SERVER_CONTEXT_CHECK_INTERVAL"
  local port="$SERVER_CONTEXT_PORT"
  main --quiet "$@"
  if [[ -f "$server_pid_file" ]]; then
    message "[setup.sh print_server_and_watchdog_pids] Server PID: $(cat "$server_pid_file")"
    ps -o pid,cmd -p "$(cat "$server_pid_file")" || true
  else
    message "[setup.sh print_server_and_watchdog_pids] Server PID file not found at $server_pid_file" >&2
  fi
  if [[ -f "$watchdog_pid_file" ]]; then
    message "[setup.sh print_server_and_watchdog_pids] Watchdog PID: $(cat "$watchdog_pid_file")"
  else
    message "[setup.sh print_server_and_watchdog_pids] Watchdog PID file not found at $watchdog_pid_file" >&2
  fi
}

if [[ "${SETUP_SH_SKIP_MAIN:-0}" != "1" ]]; then
  main "$@"
fi



