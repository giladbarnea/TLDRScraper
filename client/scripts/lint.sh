#!/usr/bin/env bash

# Define whitelist of fixable rules. Make sure these fix:"safe" in biome.json.
fixable_rules=(
  "correctness/noUnusedImports"
  "suspicious/noGlobalIsNan"
  "lint/style/useNodejsImportProtocol"
  "lint/complexity/useDateNow"
)

# Construct --only arguments
biome_args=()
for rule in "${fixable_rules[@]}"; do
  biome_args+=("--only=$rule")
done

# Fix specific rules (whitelist)
echo "Running biome lint fix for whitelisted rules..."
npx -y @biomejs/biome lint --write "${biome_args[@]}" .
echo "Running biome assist fix for whitelisted rules..."
npx -y @biomejs/biome check --formatter-enabled=false --linter-enabled=false --write
# Check and report remaining errors
echo "Running biome check..."
npx -y @biomejs/biome check . --diagnostic-level=warn
