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
  # Check mode: no modifications, exit non-zero on errors
  npx -y @biomejs/biome lint .
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
