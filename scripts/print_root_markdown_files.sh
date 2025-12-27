#!/usr/bin/env bash

# read_root_markdown_files [-q,--quiet]
# Reads all markdown files in the root directory.
# Adapted from .claude/hooks/SessionStart
function read_root_markdown_files() {
  scripts/resolve_quiet_setting.sh "$@" && return 0

  local workdir="${SERVER_CONTEXT_WORKDIR:-$PWD}"
  if [[ -z "$workdir" ]]; then
    echo "[$0][ERROR] Could not determine working directory"
    return 1
  fi

  local -a exclude=(
    CLAUDE.md # Auto-generated from AGENTS.md
    GEMINI.md # Auto-generated from AGENTS.md
    CODEX.md  # Auto-generated from AGENTS.md
  )

  function _is_excluded() {
    local _exclude
    for _exclude in "${exclude[@]}"; do
      if [[ "$1" == "${_exclude}" ]]; then
        return 0
      fi
    done
    return 1
  }

  local md_file
  local base_name
  for md_file in "$workdir"/*.md; do
    if [[ -s "$md_file" ]]; then
      base_name=$(basename "$md_file")
      if _is_excluded "$base_name"; then
        continue
      fi
      echo "<$base_name>"
      cat "$md_file"
      echo "</$base_name>"
      echo
      echo "---"
      echo
    fi
  done
}

read_root_markdown_files "$@"

