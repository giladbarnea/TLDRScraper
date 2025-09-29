#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/workspace"
RUN_DIR="$WORKDIR/.run"
SCRIPTS_DIR="$WORKDIR/scripts"
LOG_FILE="$WORKDIR/server.log"
PORT="${PORT:-5001}"

echo "[setup] Working directory: $WORKDIR"
cd "$WORKDIR"
mkdir -p "$RUN_DIR" "$SCRIPTS_DIR"

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

echo "[setup] Installing Vercel CLI (local prefix)..."
mkdir -p "$WORKDIR/.npm-global"
npm config set prefix "$WORKDIR/.npm-global" >/dev/null
export PATH="$WORKDIR/.npm-global/bin:$PATH"
if ! command -v vercel >/dev/null; then
  npm i -g vercel@latest
else
  echo "[setup] Vercel CLI already installed at $(command -v vercel)"
fi
vercel --version || true

echo "[setup] Installing Python dependencies..."
python3 -m pip --version || true
python3 -m pip install --user --break-system-packages -r "$WORKDIR/requirements.txt"

echo "[setup] Generating .env and .env.sh from current environment..."
ENV_SH="$WORKDIR/.env.sh"
ENV_FILE="$WORKDIR/.env"
ENV_KEYS_REGEX='^(OPENAI_API_TOKEN|GITHUB_API_TOKEN|EDGE_CONFIG_CONNECTION_STRING|EDGE_CONFIG_ID|VERCEL_TOKEN|BLOB_READ_WRITE_TOKEN|BLOB_STORE_BASE_URL|LOG_LEVEL|TLDR_SCRAPER_.*)='

env | egrep "$ENV_KEYS_REGEX" | sort | sed 's/^/export /' > "$ENV_SH" || true

# Ensure PATH and helpful aliases available when sourcing .env.sh
if ! grep -q '/workspace/.npm-global/bin' "$ENV_SH" 2>/dev/null; then
  echo 'export PATH="/workspace/.npm-global/bin:$PATH"' >> "$ENV_SH"
fi
echo 'alias slog="tail -n 200 /workspace/server.log"' >> "$ENV_SH" || true
echo 'alias slogf="tail -F /workspace/server.log"' >> "$ENV_SH" || true

# .env: plain KEY=VALUE lines for python-dotenv autoload
awk -F= '{print $1 "=" $2}' "$ENV_SH" | sed 's/^export //' > "$ENV_FILE" || true

echo "[setup] Sourcing .env.sh for this shell..."
set -a; . "$ENV_SH"; set +a

echo "[setup] Creating watchdog script..."
cat > "$SCRIPTS_DIR/watchdog.sh" <<'EOSH'
#!/usr/bin/env bash
set -euo pipefail
PID_FILE="/workspace/.run/server.pid"
LOG_FILE="/workspace/server.log"
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

echo "[setup] Stopping any existing server/watchdog..."
if [[ -f "$RUN_DIR/watchdog.pid" ]]; then
  (kill "$(cat "$RUN_DIR/watchdog.pid")" 2>/dev/null || true) && rm -f "$RUN_DIR/watchdog.pid"
fi
if [[ -f "$RUN_DIR/server.pid" ]]; then
  (kill "$(cat "$RUN_DIR/server.pid")" 2>/dev/null || true) && rm -f "$RUN_DIR/server.pid"
fi

echo "[setup] Starting server with nohup (port $PORT)..."
rm -f "$LOG_FILE"
nohup env PATH="/workspace/.npm-global/bin:$PATH" python3 "$WORKDIR/serve.py" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/server.pid"
sleep 1
nohup "$SCRIPTS_DIR/watchdog.sh" >> "$LOG_FILE" 2>&1 & echo $! > "$RUN_DIR/watchdog.pid"

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

cat <<'EOT'

[done] Setup complete.
Useful follow-ups:
  - source /workspace/.env.sh      # add PATH and aliases (slog/slogf)
  - ps -o pid,cmd -p $(cat /workspace/run/server.pid)
  - slog                           # show last 200 log lines
  - slogf                          # follow logs
  - curl -sS localhost:5001/ | head
  - curl -sS -H 'Content-Type: application/json' -d '{"url":"https://example.com"}' localhost:5001/api/summarize-url
  - curl -sS localhost:5001/api/prompt

Notes:
  - To enable blob uploads, set BLOB_READ_WRITE_TOKEN in /workspace/.env and rerun.
  - To avoid GitHub 401 in /api/prompt, set GITHUB_API_TOKEN in /workspace/.env and restart.
EOT

