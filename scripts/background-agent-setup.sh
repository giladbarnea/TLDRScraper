#!/usr/bin/env bash
set -euo pipefail

# Dynamic working directory (do not assume /workspace)
WORKDIR="${WORKDIR:-$PWD}"
RUN_DIR="$WORKDIR/.run"
SCRIPTS_DIR="$WORKDIR/scripts"
LOG_FILE="$WORKDIR/server.log"
PORT="${PORT:-5001}"

echo "[setup] Working directory: $WORKDIR"
cd "$WORKDIR"
mkdir -p "$RUN_DIR" "$SCRIPTS_DIR"

# Source project setup (uv, etc.) and reuse its assumptions
if [[ -f "$WORKDIR/setup.sh" ]]; then
  # shellcheck disable=SC1090
  . "$WORKDIR/setup.sh" || true
else
  echo "[setup] setup.sh not found in $WORKDIR; continuing with fallbacks" >&2
fi

echo "[setup] Checking Node.js and npm..."
if ! command -v node >/dev/null; then
  echo "[error] Node.js is required but not installed." >&2
  exit 1
fi
if ! command -v npm >/dev/null; then
  echo "[error] npm is required but not installed." >&2
  exit 1
fi
node -v || true
npm -v || true

echo "[setup] Ensuring Vercel CLI..."
if ! command -v vercel >/dev/null; then
  # Fallback to local npm prefix if setup.sh did not provide vercel
  mkdir -p "$WORKDIR/.npm-global"
  npm config set prefix "$WORKDIR/.npm-global" >/dev/null
  export PATH="$WORKDIR/.npm-global/bin:$PATH"
  if ! command -v vercel >/dev/null; then
    npm i -g vercel@latest
  fi
fi
vercel --version || true

echo "[setup] Ensuring Python dependencies via uv..."
if command -v uv >/dev/null; then
  uv sync || true
else
  echo "[warn] uv is not available; attempting to install it..." >&2
  curl -LsSf https://astral.sh/uv/install.sh | sh || true
  if command -v uv >/dev/null; then
    uv sync || true
  else
    echo "[warn] uv still unavailable; proceeding without uv sync" >&2
  fi
fi

echo "[setup] Generating .env from current environment..."
ENV_FILE="$WORKDIR/.env"
ENV_KEYS_REGEX='^(OPENAI_API_TOKEN|GITHUB_API_TOKEN|EDGE_CONFIG_CONNECTION_STRING|EDGE_CONFIG_ID|VERCEL_TOKEN|BLOB_READ_WRITE_TOKEN|BLOB_STORE_BASE_URL|LOG_LEVEL|TLDR_SCRAPER_.*)='
env | egrep "$ENV_KEYS_REGEX" | sort | sed 's/^export \{0,1\}//' > "$ENV_FILE" || true

echo "[setup] Ensuring watchdog script exists..."
if [[ ! -x "$SCRIPTS_DIR/watchdog.sh" ]]; then
  cat > "$SCRIPTS_DIR/watchdog.sh" <<'EOSH'
#!/usr/bin/env bash
set -euo pipefail
WORKDIR="${WORKDIR:-$PWD}"
PID_FILE="$WORKDIR/.run/server.pid"
LOG_FILE="$WORKDIR/server.log"
CHECK_INTERVAL="2"
if [[ ! -f "$PID_FILE" ]]; then
  echo "watchdog: missing PID file $PID_FILE" >&2
  exit 1
fi
pid="$(cat "$PID_FILE" || true)"
if [[ -z "$pid" ]]; then
  echo "watchdog: empty PID in $PID_FILE" >&2
  exit 1
fi
while true; do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "$(date -Is) watchdog: server process $pid is not running" | tee -a "$LOG_FILE"
    echo "Last 100 log lines:" | tee -a "$LOG_FILE"
    tail -n 100 "$LOG_FILE" | tee -a "$LOG_FILE"
    exit 2
  fi
  sleep "$CHECK_INTERVAL"
done
EOSH
  chmod +x "$SCRIPTS_DIR/watchdog.sh"
fi

echo "[setup] Stopping any existing server/watchdog..."
if [[ -f "$RUN_DIR/watchdog.pid" ]]; then
  (kill "$(cat "$RUN_DIR/watchdog.pid")" 2>/dev/null || true) && rm -f "$RUN_DIR/watchdog.pid"
fi
if [[ -f "$RUN_DIR/server.pid" ]]; then
  (kill "$(cat "$RUN_DIR/server.pid")" 2>/dev/null || true) && rm -f "$RUN_DIR/server.pid"
fi

echo "[setup] Starting server with nohup (port $PORT)..."
rm -f "$LOG_FILE"
nohup env PATH="$WORKDIR/.npm-global/bin:$PATH" uv run python3 "$WORKDIR/serve.py" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/server.pid"
sleep 1
nohup env WORKDIR="$WORKDIR" "$SCRIPTS_DIR/watchdog.sh" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/watchdog.pid"

echo "[setup] Server PID: $(cat "$RUN_DIR/server.pid")"
echo "[setup] Watchdog PID: $(cat "$RUN_DIR/watchdog.pid")"
ps -o pid,cmd -p "$(cat "$RUN_DIR/server.pid")" || true

echo "[setup] Quick endpoint checks..."
echo "-- / --"
curl -sS "http://localhost:$PORT/" | head -c 200 || true
echo
echo "-- /api/summarize-url (example.com) --"
curl -sS -H 'Content-Type: application/json' -d '{"url":"https://example.com"}' "http://localhost:$PORT/api/summarize-url" | head -c 400 || true
echo
echo "-- /api/prompt --"
curl -sS "http://localhost:$PORT/api/prompt" | head -c 200 || true
echo

echo "[setup] Tail last 40 log lines:"
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

