#!/usr/bin/env bash
set -eo pipefail

# Dynamic working directory (do not assume /workspace)
WORKDIR="${WORKDIR:-$PWD}"
RUN_DIR="$WORKDIR/.run"
SCRIPTS_DIR="$WORKDIR/scripts"
LOG_FILE="$WORKDIR/.run/server.log"
PORT="${PORT:-5001}"

message "[$0] Working directory: $WORKDIR"
cd "$WORKDIR"
mkdir -p "$RUN_DIR" "$SCRIPTS_DIR"

source "$WORKDIR/setup.sh"

message "[$0] Checking Node.js and npm..."
if ! is_defined "node"; then
  message "[error] Node.js is required but not installed." >&2
  exit 1
fi
if ! is_defined "npm"; then
  message "[error] npm is required but not installed." >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  message "[$0] Generating .env from current environment..."
  ENV_FILE="$WORKDIR/.env"
  ENV_KEYS_REGEX='^(OPENAI_API_TOKEN|GITHUB_API_TOKEN|EDGE_CONFIG_CONNECTION_STRING|EDGE_CONFIG_ID|VERCEL_TOKEN|BLOB_READ_WRITE_TOKEN|BLOB_STORE_BASE_URL|LOG_LEVEL|TLDR_SCRAPER_.*)='
  env | egrep "$ENV_KEYS_REGEX" | sort | sed 's/^export \{0,1\}//' > "$ENV_FILE" || true
fi


message "[$0] Stopping any existing server/watchdog..."
if [[ -f "$RUN_DIR/watchdog.pid" ]]; then
  (kill "$(cat "$RUN_DIR/watchdog.pid")" 2>/dev/null || true) && rm -f "$RUN_DIR/watchdog.pid"
fi
if [[ -f "$RUN_DIR/server.pid" ]]; then
  (kill "$(cat "$RUN_DIR/server.pid")" 2>/dev/null || true) && rm -f "$RUN_DIR/server.pid"
fi

message "[$0] Starting server with nohup (port $PORT)..."
rm -f "$LOG_FILE"
nohup env PATH="$WORKDIR/.run/npm-global/bin:$PATH" uv run python3 "$WORKDIR/serve.py" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/server.pid"
sleep 1
nohup env WORKDIR="$WORKDIR" "$SCRIPTS_DIR/watchdog.sh" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/watchdog.pid"

message "[$0] Server PID: $(cat "$RUN_DIR/server.pid")"
message "[$0] Watchdog PID: $(cat "$RUN_DIR/watchdog.pid")"
ps -o pid,cmd -p "$(cat "$RUN_DIR/server.pid")" || true

message "[$0] Quick endpoint checks..."
echo "-- / --"
curl -sS "http://localhost:$PORT/" | head -c 200 || true
echo
echo "-- /api/summarize-url (example.com) --"
curl -sS -H 'Content-Type: application/json' -d '{"url":"https://example.com"}' "http://localhost:$PORT/api/summarize-url" | head -c 400 || true
echo
echo "-- /api/prompt --"
curl -sS "http://localhost:$PORT/api/prompt" | head -c 200 || true
echo

message "[$0] Tail last 40 log lines:"
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

