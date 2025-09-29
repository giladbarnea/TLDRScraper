#!/usr/bin/env bash
set -eo pipefail

function main() {
  WORKDIR="${WORKDIR:-$PWD}"
  if [[ ! -f "$WORKDIR/serve.py" ]]; then
    echo "[error] Run this script from the project root directory." >&2
    return 1
  fi
  RUN_DIR="$WORKDIR/.run"
  SCRIPTS_DIR="$WORKDIR/scripts"
  LOG_FILE="$WORKDIR/.run/server.log"
  PORT="${PORT:-5001}"

  message "[background-agent-setup] Working directory: $WORKDIR"
  cd "$WORKDIR"
  mkdir -p "$RUN_DIR" "$SCRIPTS_DIR"

  source "$WORKDIR/setup.sh"

  message "[background-agent-setup] Checking Node.js and npm..."
  if ! isdefined "node"; then
    message "[error] Node.js is required but not installed." >&2
    return 1
  fi
  if ! isdefined "npm"; then
    message "[error] npm is required but not installed." >&2
    return 1
  fi

  message "[background-agent-setup] Installing Node.js dependencies..."
  npm install

  if [[ ! -f "$ENV_FILE" ]]; then
    message "[background-agent-setup] Generating .env from current environment..."
    ENV_FILE="$WORKDIR/.env"
    ENV_KEYS_REGEX='^(OPENAI_API_TOKEN|GITHUB_API_TOKEN|BLOB_READ_WRITE_TOKEN|BLOB_STORE_BASE_URL|LOG_LEVEL|TLDR_SCRAPER_.*)='
    env | egrep "$ENV_KEYS_REGEX" | sort | sed 's/^export \{0,1\}//' > "$ENV_FILE" || true
  fi


  message "[background-agent-setup] Stopping any existing server/watchdog..."
  if [[ -f "$RUN_DIR/watchdog.pid" ]]; then
    (kill "$(cat "$RUN_DIR/watchdog.pid")" 2>/dev/null || true) && rm -f "$RUN_DIR/watchdog.pid"
  fi
  if [[ -f "$RUN_DIR/server.pid" ]]; then
    (kill "$(cat "$RUN_DIR/server.pid")" 2>/dev/null || true) && rm -f "$RUN_DIR/server.pid"
  fi

  message "[background-agent-setup] Starting server with nohup (port $PORT)..."
  rm -f "$LOG_FILE"
  nohup env PATH="$WORKDIR/.run/npm-global/bin:$PATH" uv run python3 "$WORKDIR/serve.py" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/server.pid"
  sleep 1
  nohup env WORKDIR="$WORKDIR" "$SCRIPTS_DIR/watchdog.sh" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/watchdog.pid"

  message "[background-agent-setup] Server PID: $(cat "$RUN_DIR/server.pid")"
  message "[background-agent-setup] Watchdog PID: $(cat "$RUN_DIR/watchdog.pid")"
  ps -o pid,cmd -p "$(cat "$RUN_DIR/server.pid")" || true

  message "[background-agent-setup] Quick endpoint checks..."
  echo "-- / --"
  curl -sS "http://localhost:$PORT/" | head -c 200 || true
  echo
  echo "-- /api/summarize-url (example.com) --"
  curl -sS -H 'Content-Type: application/json' -d '{"url":"https://example.com"}' "http://localhost:$PORT/api/summarize-url" | head -c 400 || true
  echo
  echo "-- /api/prompt --"
  curl -sS "http://localhost:$PORT/api/prompt" | head -c 200 || true
  echo

  message "[background-agent-setup] Tail last 40 log lines:"
  tail -n 40 "$LOG_FILE" || true

  cat <<EOT
[done] Setup complete.
Useful follow-ups:
  - ps -o pid,cmd -p \\$(cat "$RUN_DIR/server.pid")
  - tail -n 200 "$LOG_FILE"
  - tail -F "$LOG_FILE"
  - curl -sS localhost:$PORT/ | head
  - curl -sS -H 'Content-Type: application/json' -d '{"url":"https://example.com"}' localhost:$PORT/api/summarize-url
  - curl -sS localhost:$PORT/api/prompt

Notes:
  - To enable blob uploads, set BLOB_READ_WRITE_TOKEN in "$ENV_FILE" and rerun.
  - To avoid GitHub 401 in /api/prompt, set GITHUB_API_TOKEN in "$ENV_FILE" and restart.
EOT
}

main "$@"
