#!/usr/bin/env bash
# SOURCE this file, don't run it.
set -o pipefail

export SERVER_CONTEXT_WORKDIR="${SERVER_CONTEXT_WORKDIR:-$PWD}"
_available_functions_before_setup_sh=($(declare -F | cut -d' ' -f 3))

mkdir -p "$HOME/.cache/tech-news-scraper" 1>/dev/null 2>&1
if [[ -s "$HOME/.cache/tech-news-scraper/setup-complete" ]]; then
  SETUP_QUIET=true
else
  SETUP_QUIET="${SETUP_QUIET:-false}"
fi

# Normalize SETUP_QUIET to true if it is not false or 0.
[[ "${SETUP_QUIET:-false}" == "true" || "${SETUP_QUIET}" == "1" ]] && SETUP_QUIET=true



# resolve_server_context [--workdir=WORKDIR] [--run-dir=RUN_DIR] [--log-file=LOG_FILE] [--pid-file=SERVER_PID_FILE] [--watchdog-pid-file=WATCHDOG_PID_FILE] [--check-interval=CHECK_INTERVAL] [--port=PORT]
# Resolves the server context from command line arguments and environment variables.
# Returns 0 if successful, 1 if unsuccessful.
# 
# Command line arguments and their default values:
#   --workdir=WORKDIR            Default: value of $SERVER_CONTEXT_WORKDIR if set, otherwise $PWD
#   --run-dir=RUN_DIR            Default: "$workdir/.run"
#   --log-file=LOG_FILE          Default: "$run_dir/server.log"
#   --pid-file=SERVER_PID_FILE   Default: "$run_dir/server.pid"
#   --watchdog-pid-file=WATCHDOG_PID_FILE  Default: "$run_dir/watchdog.pid"
#   --check-interval=CHECK_INTERVAL        Default: 2
#   --port=PORT                  Default: $PORT if set, otherwise 5001
# Sets the following environment variables:
#   - SERVER_CONTEXT_WORKDIR: The working directory of the server.
#   - SERVER_CONTEXT_RUN_DIR: The run directory of the server.
#   - SERVER_CONTEXT_LOG_FILE: The log file of the server.
#   - SERVER_CONTEXT_SERVER_PID_FILE: The server PID file.
#   - SERVER_CONTEXT_WATCHDOG_PID_FILE: The watchdog PID file.
#   - SERVER_CONTEXT_CHECK_INTERVAL: The check interval for the watchdog.
#   - SERVER_CONTEXT_PORT: The port for the server.
resolve_server_context() {
  local workdir="${SERVER_CONTEXT_WORKDIR:-$PWD}"
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
        
      # Quiet mode is irrelevant on the environment variable level, so we ignore it here.
      -q|--quiet|--quiet=*)
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
  port="${port:-${SERVER_CONTEXT_PORT:-5001}}"

  export SERVER_CONTEXT_WORKDIR="$workdir"
  export SERVER_CONTEXT_RUN_DIR="$run_dir"
  export SERVER_CONTEXT_LOG_FILE="$log_file"
  export SERVER_CONTEXT_SERVER_PID_FILE="$server_pid_file"
  export SERVER_CONTEXT_WATCHDOG_PID_FILE="$watchdog_pid_file"
  export SERVER_CONTEXT_CHECK_INTERVAL="$check_interval"
  export SERVER_CONTEXT_PORT="$port"
  return 0
}

isdefined(){
    command -v "$1" 1>/dev/null 2>&1
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

function error(){
  echo "[setup.sh] ERROR: $*" >&2
}

function message(){
	[[ "$SETUP_QUIET" == "false" ]] && echo "[setup.sh] $*"
	return 0
}

# # ensure_uv [-q,-quiet]
function ensure_local_bin_path(){
    local quiet="${1:-false}"
    [[ "$SETUP_QUIET" == "true" ]] && quiet=true
    
    # Cursor web agent installs to /home/ubuntu/.local/bin.
    if [[ -d "/home/ubuntu" ]]; then
        if [[ ":$PATH:" == *":/home/ubuntu/.local/bin:"* ]]; then
            [[ "$quiet" == false ]] && message "[$0] /home/ubuntu/.local/bin already present in PATH"
            return 0
        fi
        export PATH="/home/ubuntu/.local/bin:$PATH"
        [[ "$quiet" == false ]] && message "[$0] Added /home/ubuntu/.local/bin to PATH"
        return 0
    fi
    
    # The default path for local bin is $HOME/.local/bin.
    if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
        [[ "$quiet" == false ]] && message "[$0] \$HOME/.local/bin already present in PATH"
        return 0
    fi
    mkdir -p "$HOME/.local/bin"
    export PATH="$HOME/.local/bin:$PATH"
    [[ "$quiet" == false ]] && message "[$0] Added \$HOME/.local/bin to PATH"
}

# _ensure_tool [-q,-quiet] <TOOL> <INSTALL_EXPRESSION>
# Private function: idempotent installation of TOOL.
function _ensure_tool(){
  local quiet=false
  local tool=""
  local install_expression=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --quiet)
        if [[ "$2" != false && "$2" != true ]]; then
          quiet=true
        else
          quiet="$2"
          shift
        fi
        ;;
      --quiet=false)
        quiet=false
        ;;
        --quiet=true)
        quiet=true
        ;;
      -q)
        quiet=true
        ;;
      *)
        tool="$1"
        install_expression="$2"
        shift
    esac
    shift
  done
  [[ "$SETUP_QUIET" == "true" ]] && quiet=true
  local _self_name="ensure_$tool"
  if isdefined "$tool"; then
    [[ "$quiet" == false ]] && message "[$_self_name] $tool is installed and in PATH"
    return 0
  fi
  [[ "$quiet" == false ]] && message "[$_self_name] $tool is not installed, installing with '$install_expression'" >&2
  if ! eval "$install_expression" >/dev/null 2>&1; then
      message "[$_self_name] ERROR: Failed to install $tool." >&2
      return 1
  fi
  if ! isdefined "$tool"; then
      message "[$_self_name] ERROR: After installing $tool, 'command -v $tool' returned a non-zero exit code. $tool is probably installed but not in PATH." >&2
      return 1
  fi
  [[ "$quiet" == false ]] && message "[$_self_name] $tool installed and in the PATH"
  return 0
}

# ensure_uv [-q,-quiet]
# Idempotent installation of uv.
function ensure_uv(){
  _ensure_tool uv "curl -LsSf https://astral.sh/uv/install.sh | sh" "$@"
}

# uv_sync [-q,-quiet]
# Idempotent installation of Python dependencies using uv.
function uv_sync(){
    local quiet=false
    if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
        quiet=true
    elif [[ "$1" == "--quiet=true" ]]; then
        quiet=true
    elif [[ "$1" == "--quiet=false" ]]; then
        quiet=false
    fi
    [[ "$SETUP_QUIET" == "true" ]] && quiet=true
    ensure_uv --quiet || return 1
    [[ "$quiet" == false ]] && message "[$0] Running 'uv sync'..."
    local uv_sync_output
    if uv_sync_output=$(uv sync -p 3.11 2>&1); then
        [[ "$quiet" == false ]] && message "[$0] Successfully ran uv sync. Use 'uv run python3 ...' to run Python."
        return 0
    else
        error "[$0] failed to uv sync. Output:"
        echo "$uv_sync_output" >&2
        return 1
    fi
}

# # ensure_eza [-q,--quiet]
function ensure_eza(){
  _ensure_tool 'eza' 'apt install -y eza' "$@"
}
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
#         message "[$0] ERROR: Failed to create $claude_dir." >&2
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
#             message "[$0] ERROR: Failed to write $settings_path." >&2
#             return 1
#         fi
#         [[ "$quiet" == false ]] && message "[$0] Wrote default settings to $settings_path"
#     else
#         [[ "$quiet" == false ]] && message "[$0] $settings_path already exists and is non-empty"
#     fi

#     local claude_config_path="$claude_dir/claude.json"
#     if [[ ! -s "$claude_config_path" ]]; then
#         if ! cat <<'JSON' > "$claude_config_path"; then
# {
# "hasTrustDialogHooksAccepted": true,
# "hasCompletedOnboarding": true
# }
# JSON
#             message "[$0] ERROR: Failed to write $claude_config_path." >&2
#             return 1
#         fi
#         [[ "$quiet" == false ]] && message "[$0] Wrote default settings to $claude_config_path"
#     else
#         [[ "$quiet" == false ]] && message "[$0] $claude_config_path already exists and is non-empty"
#     fi

#     return 0
# }

function build_client(){
  if { builtin cd client && npm ci && npm run build; } then
    message "[$0] Successfully built client"
    builtin cd "$SERVER_CONTEXT_WORKDIR"
    return 0
  else
    message "[$0][ERROR] Failed to 'cd client && npm ci && npm run build'" >&2
    builtin cd "$SERVER_CONTEXT_WORKDIR"
    return 1
  fi
}


# main [-q,-quiet]
# Idempotent environment and dependencies setup, installation, and verification.
function main() {
  local quiet=false
  local -a args=()
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
  [[ "$SETUP_QUIET" == "true" ]] && quiet=true
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
    error "[$0] Expected serve.py at $workdir/serve.py. Current PWD: $PWD"
    return 1
  fi

  message "[$0] Working directory: $workdir"


  #region ----[ Install & Build Dependencies ]----

  mkdir -p "$run_dir"

  [[ "$quiet" == false ]] && message "[$0] Starting background dependency installation..."
  ensure_local_bin_path --quiet="$quiet"

  # Launch UV install+sync and client build in parallel background processes
  bash "$workdir/scripts/setup/ensure_uv_and_sync.sh" &
  bash "$workdir/scripts/setup/build_client.sh" &

  [[ "$quiet" == false ]] && message "[$0] UV sync and client build running in background..."
  
  #region ----[ Prepare & Print Docs ]----
  
  [[ "$quiet" == false ]] && message "[$0] Configuring git hooks..."
  if [[ -d "$workdir/.githooks" ]]; then
    if git config core.hooksPath .githooks; then
      [[ "$quiet" == false ]] && message "[$0] Git hooks configured to use .githooks directory"
      
      
      if [[ -x "$workdir/.githooks/pre-merge-commit" ]]; then
        [[ "$quiet" == false ]] && message "[$0] Running pre-merge-commit hook to generate PROJECT_STRUCTURE.md..."
        (builtin cd "$workdir" && ./.githooks/pre-merge-commit)
        [[ "$quiet" == false && -f PROJECT_STRUCTURE.md ]] && message "[$0] Generated PROJECT_STRUCTURE.md via git hook"
      fi
    fi
  fi
  
  #region ----[ Env Vars Validation ]----
    
  [[ "$quiet" == false ]] && message "[$0] Checking for required environment variables..."
  if [[ -f "$workdir/.env" ]]; then
      local line
      command grep --color=never -E -v '^(\s*#|$)' "$workdir/.env" | while read -r line; do
        eval export "$line"
      done
  fi
  local -a expected_env_vars=(
    GITHUB_API_TOKEN
    OPENAI_API_KEY
    FIRECRAWL_API_KEY
    SUPABASE_PUBLISHABLE_KEY
    SUPABASE_DATABASE_PASSWORD
    SUPABASE_SECRET_KEY
    SUPABASE_URL
  )
  local pattern="($(IFS='|'; echo "${expected_env_vars[*]}"))"
  local existing_env_vars="$(env | command grep --color=never -E "$pattern" | sort -u)"
  local -a missing_env_vars=()
  local env_var_name
  for env_var_name in "${expected_env_vars[@]}"; do
    if ! command grep --color=never -E -q "${env_var_name}=.+" <<< "$existing_env_vars"; then
      missing_env_vars+=("$env_var_name")
    fi
  done
  if [[ "${#missing_env_vars[@]}" -gt 0 ]]; then
    error "[$0] Environment variables missing: ${missing_env_vars[*]}. Stop and tell the user."
    return 1
  fi

  if [[ "$quiet" == false ]]; then
    message "[$0] Setup complete successfully. Available env vars: ${expected_env_vars[*]}"
  fi

  echo 1 > "$HOME/.cache/tech-news-scraper/setup-complete"
}

# region Watchdog

WATCHDOG_DOC="Watchdog process: watch the server process using given/resolved SERVER_CONTEXT_SERVER_PID_FILE."
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

  if [[ ! -f "$server_pid_file" ]]; then
    error "[$0] missing PID file $server_pid_file"
    return 1
  fi

  local server_pid
  server_pid="$(cat "$server_pid_file" 2>/dev/null || true)"
  if [[ -z "$server_pid" ]]; then
    error "[$0] empty PID in $server_pid_file"
    return 1
  fi
  
  # Start watching the server process. Error out and return 2 if the server if not kill -0 $server_pid.
  while true; do
    if ! kill -0 "$server_pid" 2>/dev/null; then
      {
        error "[$0] $(date -Is) watchdog server process $server_pid is not running"
        error "[$0] Last 100 log lines:"
        if [[ -f "$log_file" ]]; then
          tail -n 100 "$log_file"
        else
          error "[$0] Log file $log_file not found."
        fi
      } | tee -a "$log_file"
      message "[$0][ERROR] Returning 2" 1>&2
      return 2
    fi
    message "[$0] Sleeping $check_interval seconds"
    sleep "$check_interval"
  done
}
# endregion Watchdog

START_SERVER_AND_WATCHDOG_DOC="Start the server and watchdog processes in the background given specified/resolved environment variables. Tees the server logs log file. Usage: source setup.sh && start_server_and_watchdog"
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
  message "[$0] Starting server with nohup (port $port)..."
  rm -f "$log_file" "$server_pid_file" "$watchdog_pid_file"
  mkdir -p "$run_dir"
  
  # Start the server in the background and write the PID to $server_pid_file.
  (
    builtin cd "$workdir"
    PORT="$port" uv run python3.11 "$workdir/serve.py" >> "$log_file" 2>&1 &
    echo $! > "$server_pid_file"
    wait
  ) &
  local server_pid=""
  
  # Wait for the server to start and load the PID into $server_pid. 5-second timeout.
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
    error "[$0] Failed to capture server PID."
    return 1
  fi
  message "[$0] Server started with PID $server_pid"
  sleep 1
  local watchdog_command="builtin cd \"$workdir\" && SETUP_SH_SKIP_MAIN=1 source \"$workdir/setup.sh\" && watchdog --workdir=\"$workdir\" --run-dir=\"$run_dir\" --log-file=\"$log_file\" --pid-file=\"$server_pid_file\" --watchdog-pid-file=\"$watchdog_pid_file\" --check-interval=\"$check_interval\" --port=\"$port\""
  nohup bash -lc "$watchdog_command" >> "$log_file" 2>&1 &
  echo $! > "$watchdog_pid_file"
  message "[$0] Watchdog started with PID $(cat "$watchdog_pid_file")"
  print_server_and_watchdog_pids "$@"
}

KILL_SERVER_AND_WATCHDOG_DOC="Idempotent stop of the server and watchdog processes. Usage: source setup.sh && kill_server_and_watchdog"
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
  message "[$0] Assessing existing server/watchdog..."
  if [[ -f "$watchdog_pid_file" ]]; then
    message "[$0] Watchdog PID file found, stopping watchdog..."
    kill "$(cat "$watchdog_pid_file")"
    rm -f "$watchdog_pid_file"
  fi
  if [[ -f "$server_pid_file" ]]; then
    message "[$0] Server PID file found, stopping server..."
    kill "$(cat "$server_pid_file")"
    rm -f "$server_pid_file"
  fi
}

PRINT_SERVER_AND_WATCHDOG_PIDS_DOC="Helper tool: print the server and watchdog PIDs. Usage: source setup.sh && print_server_and_watchdog_pids"
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
  local server_pid="" watchdog_pid=""
  if [[ -f "$server_pid_file" ]]; then
    server_pid="$(cat "$server_pid_file")"
  else
    error "[$0] Server PID file not found at $server_pid_file"
    return 1
  fi
  if [[ -f "$watchdog_pid_file" ]]; then
    watchdog_pid="$(cat "$watchdog_pid_file")"
  else
    error "[$0] Watchdog PID file not found at $watchdog_pid_file"
    return 1
  fi
  message "[$0] server pid: $server_pid. watchdog pid: $watchdog_pid."
}

if [[ "${SETUP_SH_SKIP_MAIN:-0}" != "1" ]]; then
  main "$@"
fi


_available_functions_after_setup_sh=($(declare -F | cut -d' ' -f 3))
_new_functions=($(comm -23 <(echo "${_available_functions_after_setup_sh[@]}") <(echo "${_available_functions_before_setup_sh[@]}")))
_new_functions=($(xargs -n1 <<< ${_new_functions[@]} | grep -e server -e watchdog || true))
if [[ ${#_new_functions[@]} -gt 0 ]]; then
  _new_functions_formatted="$(echo ${_new_functions[@]} | tr ' ' ', ')"
  message "[DONE] New functions available for use after sourcing setup.sh: ${_new_functions_formatted}"
  message "  - watchdog: ${WATCHDOG_DOC}"
  message "  - start_server_and_watchdog: ${START_SERVER_AND_WATCHDOG_DOC}"
  message "  - kill_server_and_watchdog: ${KILL_SERVER_AND_WATCHDOG_DOC}"
  message "  - print_server_and_watchdog_pids: ${PRINT_SERVER_AND_WATCHDOG_PIDS_DOC}"
fi