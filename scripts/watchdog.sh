#!/usr/bin/env bash
set -euo pipefail
PID_FILE="/workspace/run/server.pid"
LOG_FILE="/workspace/server.log"
CHECK_INTERVAL="2"
if [[ ! -f "$PID_FILE" ]]; then echo "watchdog: missing PID file $PID_FILE" >&2; exit 1; fi
pid="$(cat "$PID_FILE" || true)"
if [[ -z "$pid" ]]; then echo "watchdog: empty PID in $PID_FILE" >&2; exit 1; fi
while true; do if ! kill -0 "$pid" 2>/dev/null; then echo "$(date -Is) watchdog: server process $pid is not running" | tee -a "$LOG_FILE"; echo "Last 100 log lines:" | tee -a "$LOG_FILE"; tail -n 100 "$LOG_FILE" | tee -a "$LOG_FILE"; exit 2; fi; sleep "$CHECK_INTERVAL"; done
