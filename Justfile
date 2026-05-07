set shell := ["bash", "-uc"]
set positional-arguments

run_dir := ".run"
backend_pid_file := ".run/backend.pid"
frontend_pid_file := ".run/frontend.pid"
backend_log_file := ".run/backend.log"
frontend_log_file := ".run/frontend.log"

dev *arguments='':
  #!/usr/bin/env bash
  set -euo pipefail

  run_dir='{{run_dir}}'
  backend_pid_file='{{backend_pid_file}}'
  frontend_pid_file='{{frontend_pid_file}}'
  backend_log_file='{{backend_log_file}}'
  frontend_log_file='{{frontend_log_file}}'
  background_mode=true

  for argument in "$@"; do
    if [[ -z "$argument" || "$argument" == "--" ]]; then
      continue
    fi

    if [[ "$argument" == "--foreground" ]]; then
      background_mode=false
      continue
    fi

    echo "Unknown dev argument: $argument" >&2
    exit 1
  done

  mkdir -p "$run_dir"

  backend_is_running=false
  frontend_is_running=false

  if [[ -f "$backend_pid_file" ]] && kill -0 "$(cat "$backend_pid_file")" 2>/dev/null; then
    backend_is_running=true
    echo "Backend already running with PID $(cat "$backend_pid_file")" >&2
  fi

  if [[ -f "$frontend_pid_file" ]] && kill -0 "$(cat "$frontend_pid_file")" 2>/dev/null; then
    frontend_is_running=true
    echo "Frontend already running with PID $(cat "$frontend_pid_file")" >&2
  fi

  if [[ "$backend_is_running" == true && "$frontend_is_running" == true ]]; then
    exit 1
  fi

  if [[ "$backend_is_running" == true || "$frontend_is_running" == true ]]; then
    echo "Warning: zombie dev state detected; only one process is running" >&2
    exit 1
  fi

  collect_child_processes() {
    local process_id="$1"
    local child_process_id

    while read -r child_process_id; do
      [[ -n "$child_process_id" ]] || continue
      collect_child_processes "$child_process_id"
      echo "$child_process_id"
    done < <(pgrep -P "$process_id" || true)
  }

  stop_process_tree() {
    local process_id="$1"
    local child_process_id

    kill -0 "$process_id" 2>/dev/null || return

    while read -r child_process_id; do
      [[ -n "$child_process_id" ]] || continue
      kill -TERM "$child_process_id" 2>/dev/null || true
    done < <(collect_child_processes "$process_id")

    kill -TERM "$process_id" 2>/dev/null || true
  }

  cleanup() {
    local backend_pid=""
    local frontend_pid=""

    [[ -f "$backend_pid_file" ]] && backend_pid="$(cat "$backend_pid_file")"
    [[ -f "$frontend_pid_file" ]] && frontend_pid="$(cat "$frontend_pid_file")"

    [[ -n "$backend_pid" ]] && stop_process_tree "$backend_pid"
    [[ -n "$frontend_pid" ]] && stop_process_tree "$frontend_pid"

    rm -f "$backend_pid_file" "$frontend_pid_file"
  }

  if [[ "$background_mode" == true ]]; then
    nohup bash -lc 'exec uv run serve.py' > "$backend_log_file" 2>&1 &
    backend_pid=$!
    echo "$backend_pid" > "$backend_pid_file"

    nohup bash -lc 'cd client && exec npm run dev -- --host' > "$frontend_log_file" 2>&1 &
    frontend_pid=$!
    echo "$frontend_pid" > "$frontend_pid_file"

    sleep 1

    if ! kill -0 "$backend_pid" 2>/dev/null || ! kill -0 "$frontend_pid" 2>/dev/null; then
      cleanup
      echo "Failed to start dev processes in background" >&2
      exit 1
    fi

    echo "Started backend ($backend_pid) -> $backend_log_file"
    echo "Started frontend ($frontend_pid) -> $frontend_log_file"
    exit 0
  fi

  trap cleanup EXIT INT TERM

  uv run serve.py &
  backend_pid=$!
  echo "$backend_pid" > "$backend_pid_file"

  bash -lc 'cd client && exec npm run dev -- --host' &
  frontend_pid=$!
  echo "$frontend_pid" > "$frontend_pid_file"

  wait "$backend_pid" "$frontend_pid"

stop:
  #!/usr/bin/env bash
  set -euo pipefail

  backend_pid_file='{{backend_pid_file}}'
  frontend_pid_file='{{frontend_pid_file}}'

  collect_child_processes() {
    local process_id="$1"
    local child_process_id

    while read -r child_process_id; do
      [[ -n "$child_process_id" ]] || continue
      collect_child_processes "$child_process_id"
      echo "$child_process_id"
    done < <(pgrep -P "$process_id" || true)
  }

  stop_process_tree() {
    local process_id="$1"
    local child_process_id

    kill -0 "$process_id" 2>/dev/null || return 1

    while read -r child_process_id; do
      [[ -n "$child_process_id" ]] || continue
      kill -TERM "$child_process_id" 2>/dev/null || true
    done < <(collect_child_processes "$process_id")

    kill -TERM "$process_id" 2>/dev/null || true
  }

  stop_process() {
    local pid_file="$1"
    local label="$2"

    if [[ ! -f "$pid_file" ]]; then
      echo "$label is not running"
      return
    fi

    local process_id
    process_id="$(cat "$pid_file")"

    if ! stop_process_tree "$process_id"; then
      rm -f "$pid_file"
      echo "$label pid file was stale"
      return
    fi

    rm -f "$pid_file"
    echo "Stopped $label"
  }

  stop_process "$backend_pid_file" backend
  stop_process "$frontend_pid_file" frontend

logs:
  #!/usr/bin/env bash
  set -euo pipefail

  run_dir='{{run_dir}}'
  backend_log_file='{{backend_log_file}}'
  frontend_log_file='{{frontend_log_file}}'

  mkdir -p "$run_dir"
  touch "$backend_log_file" "$frontend_log_file"

  tail -n +1 -F "$backend_log_file" "$frontend_log_file" 2>/dev/null |
    awk -v backend_log_file="$backend_log_file" -v frontend_log_file="$frontend_log_file" '
      function switch_to(stream_name) {
        if (current_stream != "" && current_stream != stream_name) {
          print "</" current_stream ">"
        }
        if (current_stream != stream_name) {
          current_stream = stream_name
          print "<" current_stream ">"
          fflush()
        }
      }

      $0 == "==> " backend_log_file " <==" {
        switch_to("server")
        next
      }

      $0 == "==> " frontend_log_file " <==" {
        switch_to("client")
        next
      }

      {
        print
        fflush()
      }

      END {
        if (current_stream != "") {
          print "</" current_stream ">"
        }
      }
    '

client-lint:
  cd client && ./scripts/lint.sh
