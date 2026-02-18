#!/usr/bin/env bash
set -eo pipefail

# Lint pipeline: knip (dead code) → biome (lint + imports)
#
# Knip: detects unused files, dependencies, and exports.
#   --fix removes unused exports and dependencies automatically.
#   Unused files and remaining issues are reported as warnings.
#
# Biome: configured via biome.json.
#   Fix mode: auto-fixes safe rules (unused imports, import ordering, etc.)
#   Check mode (CI): reports issues, exits non-zero on errors.
#
# Usage:
#   ./lint.sh              # Fix mode: auto-fix issues
#   CI=true ./lint.sh      # Check mode: report only, exit 1 on errors
#   DRY_RUN=1 ./lint.sh    # Check mode: for pre-commit hooks

IS_CHECK_MODE=false
if [ "${CI:-false}" = "true" ] || [ "${DRY_RUN:-0}" = "1" ]; then
  IS_CHECK_MODE=true
fi

# --- Knip: dead code detection ---
if [ "$IS_CHECK_MODE" = true ]; then
  npx -y knip --reporter compact || true
else
  npx -y knip --fix --reporter compact || true
fi

# --- Biome: lint + import organization ---
if [ "$IS_CHECK_MODE" = true ]; then
  npx -y @biomejs/biome lint .
  npx -y @biomejs/biome check \
    --formatter-enabled=false \
    --linter-enabled=false \
    --assist-enabled=true
else
  npx -y @biomejs/biome lint --write .
  npx -y @biomejs/biome check \
    --formatter-enabled=false \
    --linter-enabled=false \
    --assist-enabled=true \
    --write \
    2>/dev/null || true
fi
