#!/usr/bin/env bash
set -eo pipefail

# Orthogonal to lint.sh: only formats code, no linting.
# Format configuration is in biome.json (uses defaults if not specified).
#
# Usage:
#   ./format.sh              # Format mode: auto-format files
#   CI=true ./format.sh      # Check mode: report formatting issues, exit 1 on errors
#   DRY_RUN=1 ./format.sh    # Check mode: for pre-commit hooks or previewing changes

if [ "${CI:-false}" = "true" ] || [ "${DRY_RUN:-0}" = "1" ]; then
  # Check mode: report what needs formatting, don't modify files
  npx -y @biomejs/biome format \
    --no-errors-on-unmatched \
    --files-ignore-unknown=true \
    .
else
  # Format mode: auto-format all files
  npx -y @biomejs/biome format --write \
    --no-errors-on-unmatched \
    --files-ignore-unknown=true \
    .
fi
