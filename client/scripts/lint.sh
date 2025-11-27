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

# Step 1: Lint and auto-fix
# Fixes rules marked fix:"safe", reports unfixable issues
npx -y @biomejs/biome lint --write .

# Step 2: Organize imports (assist)
npx -y @biomejs/biome check \
    --formatter-enabled=false \
    --linter-enabled=false \
    --assist-enabled=true \
    --write \
    2>/dev/null || true
