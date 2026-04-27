set shell := ["bash", "-uc"]

dev:
  #!/usr/bin/env bash
  set -euo pipefail
  trap 'kill 0' EXIT INT TERM
  uv run serve.py &
  cd client
  npm run dev -- --host
