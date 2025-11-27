#!/usr/bin/env bash
set -eo pipefail

# Single-pass lint: fix what's fixable, report what's not.
# Configuration is in biome.json:
#   - Rules with fix:"safe" are auto-fixed silently
#   - Rules without fix config are reported as warnings/errors
#
# Fixable rules (fix:"safe"):
#   - correctness/noUnusedImports
#   - suspicious/noGlobalIsNan
#   - style/useNodejsImportProtocol
#   - complexity/useDateNow
#   - source/organizeImports (via assist)
#
# Check-only rules (no fix, just warn):
#   - correctness/useExhaustiveDependencies
#   - correctness/useHookAtTopLevel
#   - correctness/noChildrenProp
#   - correctness/noNestedComponentDefinitions
#   - correctness/noReactPropAssignments
#   - correctness/noRenderReturnValue
#   - correctness/useJsxKeyInIterable
#   - style/useReactFunctionComponents
#
# Usage:
#   ./lint.sh              # Fix mode: auto-fix issues
#   CI=true ./lint.sh      # Check mode: report issues, exit 1 on errors (CI auto-detects)
#   DRY_RUN=1 ./lint.sh    # Check mode: for pre-commit hooks

if [ "${CI:-false}" = "true" ] || [ "${DRY_RUN:-0}" = "1" ]; then
  # CI/Check mode: no modifications, exit non-zero on errors
  # Use 'biome ci' command (not 'biome check') - it's read-only and optimized for CI

  # Critical flags for CI reliability:
  # --formatter-enabled=false: Only check linting, not formatting (normal mode doesn't format either)
  # --no-errors-on-unmatched: Don't fail if no files match patterns (avoids false failures)
  # --files-ignore-unknown: Skip non-JS/TS files without erroring (e.g., .md, .yml)
  # --error-on-warnings: Treat warnings as errors for strict enforcement
  #
  # Note on --changed flag: We intentionally DON'T use --changed here because:
  # - Requires proper git history (fetch-depth: 0) which isn't always available
  # - Many users report it's unreliable in CI environments
  # - GitHub Actions workflow uses manual 'git diff' for more reliable change detection
  # - See: https://github.com/biomejs/biome/discussions/4896

  npx -y @biomejs/biome ci \
    --formatter-enabled=false \
    --no-errors-on-unmatched \
    --files-ignore-unknown=true \
    --error-on-warnings \
    .

  npx -y @biomejs/biome check \
    --formatter-enabled=false \
    --linter-enabled=false \
    --assist-enabled=true
else
  # Fix mode: auto-fix and organize imports
  npx -y @biomejs/biome lint --write .
  npx -y @biomejs/biome check \
    --formatter-enabled=false \
    --linter-enabled=false \
    --assist-enabled=true \
    --write \
    2>/dev/null || true
fi
