#!/usr/bin/env bash
set -o pipefail

if [[ -f setup.sh ]]; then
  source setup.sh
else
  echo "[background-agent-setup.sh] ERROR: Sourcethis script from the project root directory. Current PWD: $PWD" >&2
fi

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

  source "$PWD/setup.sh"

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
  [[ "$quiet" == false ]] && message "[background-agent-setup.sh main] Setup complete successfully. Available: $env_vars. $(cat <<EOT
Available functions:
  - kill_server_and_watchdog
  - start_server_and_watchdog
  - print_server_and_watchdog_pids
  - smoke_test
EOT
)"
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
  
function smoke_test() {
  main --quiet
  message "[background-agent-setup.sh smoke_test] Quick endpoint checks..."
  local local_yyyymmdd="$(date +%Y-%m-%d)"
  echo "-- / --"
  curl -sS "http://localhost:$PORT/" | head -c 200 || true
  echo
  echo "-- /api/summarize-url (example.com) --"
  curl -sS -H 'Content-Type: application/json' -d '{"url":"https://example.com"}' "http://localhost:$PORT/api/summarize-url" | head -c 400 || true
  echo
  echo "-- /api/prompt --"
  curl -sS "http://localhost:$PORT/api/prompt" | head -c 200 || true
  echo
  echo "-- /api/scrape --"
  curl -sS -H 'Content-Type: application/json' -d "{\"start_date\":\"$local_yyyymmdd\", \"end_date\":\"$local_yyyymmdd\"}" "http://localhost:$PORT/api/scrape" | head -c 200 || true
  echo
  echo "-- /api/remove-url --"
  curl -sS -H 'Content-Type: application/json' -d '{"url":"http://example.com/removed"}' "http://localhost:$PORT/api/remove-url" | head -c 200 || true
  echo
  echo "-- /api/cache-mode (GET) --"
  curl -sS "http://localhost:$PORT/api/cache-mode" | head -c 200 || true
  echo
  echo "-- /api/cache-mode (POST) --"
  curl -sS -H 'Content-Type: application/json' -d '{"cache_mode":"disabled"}' "http://localhost:$PORT/api/cache-mode" | head -c 200 || true
  echo
  echo "-- /api/invalidate-cache --"
  curl -sS -H 'Content-Type: application/json' -d "{\"start_date\":\"$local_yyyymmdd\", \"end_date\":\"$local_yyyymmdd\"}" "http://localhost:$PORT/api/invalidate-cache" | head -c 200 || true
  echo
  echo "-- /api/invalidate-date-cache --"
  curl -sS -H 'Content-Type: application/json' -d "{\"date\":\"$local_yyyymmdd\"}" "http://localhost:$PORT/api/invalidate-date-cache" | head -c 200 || true
  echo

  message "[background-agent-setup.sh smoke_test] Tail last 40 log lines:"
  tail -n 40 "$LOG_FILE" || true
}

main "$@"
