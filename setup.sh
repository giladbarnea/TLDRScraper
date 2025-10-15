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

function ensure_claude_code(){
        local quiet=false
        if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
                quiet=true
    elif [[ "$1" == "--quiet=true" ]]; then
        quiet=true
    elif [[ "$1" == "--quiet=false" ]]; then
        quiet=false
        fi

    ensure_local_bin_path "$quiet"
    if isdefined claude; then
        local version_output
        if version_output=$(claude --version 2>&1); then
            [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_code] claude code already installed: $(decolor "$version_output")"
            return 0
        fi
        message "[setup.sh ensure_claude_code] claude code detected but failed to run 'claude --version'." >&2
        return 1
    fi

    message "[setup.sh ensure_claude_code] Installing claude code with 'npm install -g @anthropic-ai/claude-code'" >&2
    if ! npm install -g @anthropic-ai/claude-code; then
        message "[setup.sh ensure_claude_code] ERROR: Failed to install claude code." >&2
        return 1
    fi

    local version_output
    if version_output=$(claude --version 2>&1); then
        [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_code] Installed claude code: $(decolor "$version_output")"
        return 0
    fi

    message "[setup.sh ensure_claude_code] ERROR: claude code installed but 'claude --version' failed." >&2
    return 1
}

function ensure_codex(){
        local quiet=false
        if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
                quiet=true
    elif [[ "$1" == "--quiet=true" ]]; then
        quiet=true
    elif [[ "$1" == "--quiet=false" ]]; then
        quiet=false
        fi

    ensure_local_bin_path "$quiet"
    if isdefined codex; then
        local version_output
        if version_output=$(codex --version 2>&1); then
            [[ "$quiet" == false ]] && message "[setup.sh ensure_codex] codex already installed: $(decolor "$version_output")"
            return 0
        fi
        message "[setup.sh ensure_codex] codex detected but failed to run 'codex --version'." >&2
        return 1
    fi

    message "[setup.sh ensure_codex] Installing codex with 'npm install -g @openai/codex'" >&2
    if ! npm install -g @openai/codex; then
        message "[setup.sh ensure_codex] ERROR: Failed to install codex." >&2
        return 1
    fi

    local version_output
    if version_output=$(codex --version 2>&1); then
        [[ "$quiet" == false ]] && message "[setup.sh ensure_codex] Installed codex: $(decolor "$version_output")"
        return 0
    fi

    message "[setup.sh ensure_codex] ERROR: codex installed but 'codex --version' failed." >&2
    return 1
}

function ensure_claude_settings(){
    local quiet=false
    if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
        quiet=true
    elif [[ "$1" == "--quiet=true" ]]; then
        quiet=true
    elif [[ "$1" == "--quiet=false" ]]; then
        quiet=false
    fi

    local claude_dir="$HOME/.claude"
    if ! mkdir -p "$claude_dir"; then
        message "[setup.sh ensure_claude_settings] ERROR: Failed to create $claude_dir." >&2
        return 1
    fi

    local settings_path="$claude_dir/settings.json"
    if [[ ! -s "$settings_path" ]]; then
        if ! cat <<'JSON' > "$settings_path"; then
{
  
  "permissions": {
      "defaultMode": "bypassPermissions"
  },
  "env": {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
    "DISABLE_AUTOUPDATER": 1,
    "DISABLE_NON_ESSENTIAL_MODEL_CALLS": 1,
    "DISABLE_TELEMETRY": 1
  }
}
JSON
            message "[setup.sh ensure_claude_settings] ERROR: Failed to write $settings_path." >&2
            return 1
        fi
        [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_settings] Wrote default settings to $settings_path"
    else
        [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_settings] $settings_path already exists and is non-empty"
    fi

    local claude_config_path="$claude_dir/claude.json"
    if [[ ! -s "$claude_config_path" ]]; then
        if ! cat <<'JSON' > "$claude_config_path"; then
{
"hasTrustDialogHooksAccepted": true,
"hasCompletedOnboarding": true
}
JSON
            message "[setup.sh ensure_claude_settings] ERROR: Failed to write $claude_config_path." >&2
            return 1
        fi
        [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_settings] Wrote default settings to $claude_config_path"
    else
        [[ "$quiet" == false ]] && message "[setup.sh ensure_claude_settings] $claude_config_path already exists and is non-empty"
    fi

    return 0
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
    echo "[setup.sh main] ERROR: Source this script from the project root directory. Current PWD: $PWD" >&2
    return 1
  fi
  export RUN_DIR="$PWD/.run"
  export SCRIPTS_DIR="$PWD/scripts"
  export LOG_FILE="$RUN_DIR/server.log"
  export PORT="${PORT:-5001}"

  message "[setup.sh main] Working directory: $PWD"
  mkdir -p "$RUN_DIR"


  [[ "$quiet" == false ]] && message "[setup.sh main] Ensuring dependencies..."
  local ensure_uv_success=true uv_sync_success=true ensure_claude_success=true ensure_claude_settings_success=true ensure_codex_success=true
  ensure_uv --quiet="$quiet" || ensure_uv_success=false
  uv_sync --quiet="$quiet" || uv_sync_success=false
  ensure_claude_code --quiet="$quiet" || ensure_claude_success=false
  ensure_claude_settings --quiet="$quiet" || ensure_claude_settings_success=false
  ensure_codex --quiet="$quiet" || ensure_codex_success=false

  if ! "$ensure_uv_success" || ! "$uv_sync_success" || ! "$ensure_claude_success" || ! "$ensure_claude_settings_success" || ! "$ensure_codex_success"; then
    message "[setup.sh main] Failed to install dependencies. Please check the output above." >&2
    return 1
  fi
  
  [[ "$quiet" == false ]] && message "[setup.sh main] Checking for required environment variables..."
  if [[ -f .env ]]; then
      command grep --color=never -E -v '^(\s*#|$)' .env | while read -r line; do
        eval export "$line"
      done
  fi
  local env_vars="$(env | egrep '(ANTHROPIC|OPENAI|GITHUB|BLOB|TLDR)' | sort -u)"
  local -a env_var_names=(
    'BLOB_READ_WRITE_TOKEN'
    'BLOB_STORE_BASE_URL'
    'GITHUB_API_TOKEN'
    'OPENAI_API_KEY'
    'ANTHROPIC_API_KEY'
  )
  local -a env_vars_missing=()
  local env_var_name
  for env_var_name in "${env_var_names[@]}"; do
    if ! egrep -q "${env_var_name}=.+" <<< "$env_vars"; then
      env_vars_missing+=("$env_var_name")
    fi
  done
  if [[ "${#env_vars_missing[@]}" -gt 0 ]]; then
    message "[setup.sh main] Environment variables missing: ${env_vars_missing[@]}. Stop and tell the user." >&2
    return 1
  fi
  if [[ "$quiet" == false ]]; then
    message "[setup.sh main] Setup complete successfully. Available: $env_vars.

**Use cli.py sparingly to verify your work.**

Claude code configuration:
- ANTHROPIC_API_KEY detected in the environment. Use it with 'claude' instead of logging in.
- Base command is 'claude'. To keep claude code non-interactive, do not run bare 'claude'; run 'claude --help' and 'claude <subcommand> --help' recursively to understand scripted usage.
- Verify the installation with 'claude --version'.
- '--dangerously-skip-permissions' bypasses Claude's permission prompts; only use it in trusted sandboxes.
- Example invocation: claude --print --dangerously-skip-permissions \"\$(cat /tmp/ad-hoc-tmp-prompt-file.md)\"
- Use Claude Sonnet 4.5 when choosing a model.

Codex configuration:
- OPENAI_API_KEY detected in the environment. Use it with 'codex' instead of logging in.
- Base command is 'codex'. To keep codex non-interactive, do not run bare 'codex'.
- Verify the installation with 'codex --version'.
- Always use the '--dangerously-bypass-approvals-and-sandbox' cli option when invoking codex.
- Always use codex with the 'exec' subcommand which ensures a non-interactive command.
- Basic invocation: `codex exec --dangerously-bypass-approvals-and-sandbox \"\$(cat /tmp/ad-hoc-tmp-prompt-file.md)\"`
- You are encouraged to explore additional cmdline codex usages by running 'codex --help' and multiple relevant 'codex <subcommand> --help'
- Don't specify a model. Let the default be used implicitly.
"
  fi
}

function kill_server_and_watchdog() {
  main --quiet
  message "[setup.sh main] Assessing existing server/watchdog..."
  if [[ -f "$RUN_DIR/watchdog.pid" ]]; then
    message "[setup.sh main] Watchdog PID file found, stopping watchdog..."
    kill "$(cat "$RUN_DIR/watchdog.pid")"
    rm -f "$RUN_DIR/watchdog.pid"
  fi
  if [[ -f "$RUN_DIR/server.pid" ]]; then
    message "[setup.sh main] Server PID file found, stopping server..."
    kill "$(cat "$RUN_DIR/server.pid")"
    rm -f "$RUN_DIR/server.pid"
  fi
}

function start_server_and_watchdog() {
  main --quiet
  message "[setup.sh start_server_and_watchdog] Starting server with nohup (port $PORT)..."
  rm -f "$LOG_FILE"
  uv run python3 "$PWD/serve.py" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/server.pid"
  sleep 1
  nohup env WORKDIR="$PWD" "$SCRIPTS_DIR/watchdog.sh" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/watchdog.pid"
}

function print_server_and_watchdog_pids() {
  main --quiet
  message "[setup.sh print_server_and_watchdog_pids] Server PID: $(cat "$RUN_DIR/server.pid")"
  message "[setup.sh print_server_and_watchdog_pids] Watchdog PID: $(cat "$RUN_DIR/watchdog.pid")"
  ps -o pid,cmd -p "$(cat "$RUN_DIR/server.pid")" || true
}

main "$@"



