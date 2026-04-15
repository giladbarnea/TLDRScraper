#!/bin/bash

_HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_HOOKS_DIR/sync-subdir.sh"

# _ensure_agent_symlinks [workdir=$PWD]
# Ensures that `.agents/{skills,agents}` are symlinks to the real CLI agent configuration dirs.
function _ensure_agent_symlinks() {
  local dot_dirs=(".claude" ".codex" ".gemini" ".pi")
  local workdir="${1:-${SERVER_CONTEXT_WORKDIR:-$PWD}}"
  local dir target link_path current_target
  for dir in "${dot_dirs[@]}"; do
    mkdir -p "$workdir/$dir"
    for target in "agents" "skills"; do
      link_path="$workdir/$dir/$target"
      if [[ -L "$link_path" ]]; then
        current_target=$(readlink "$link_path")
        if [[ "$current_target" != "../.agents/$target" ]]; then
          rm "$link_path"
          ln -s "../.agents/$target" "$link_path"
        fi
      else
        rm -rf "$link_path"
        ln -s "../.agents/$target" "$link_path"
      fi
    done
  done
}

# _generate_project_structure [workdir=$PWD]
# Generates the project structure markdown file and updates the last updated frontmatter field.
function _generate_project_structure() {
  local workdir="${SERVER_CONTEXT_WORKDIR:-$PWD}"
  export PATH="${HOME}/.local/bin:${PATH}"
  local -a ignore_glob_patterns=(
    '.git'
    'vendor'
    'node_modules'
    '__pycache__'
    '*.pyc'
    '.venv'
    'static'
    '*.vscode'
    '*.cursor'
    'experimental'
    'thoughts/done'
    'docs'
    '.run'
    '.codex'
    '.gemini'
    '.pi/npm'
    'tests'
    '.*/skills'
    '.*/agents'
    '.claude/hooks'
  )
  local ignore_glob
  local old_ifs="$IFS"
  IFS='|'
  ignore_glob="${ignore_glob_patterns[*]}"
  IFS="$old_ifs"
  uv run python3 scripts/generate_tree.py \
    --classify \
    --icons \
    --tree \
    --git-ignore \
    --all \
    --ignore-glob "$ignore_glob" \
    . >"PROJECT_STRUCTURE.md"
  update_markdown_last_updated "PROJECT_STRUCTURE.md" "$(date -u +"%Y-%m-%d %H:%M")"
}

function update_markdown_last_updated() {
  local file_path="$1"
  local timestamp="$2"
  uv run python3 - "$file_path" "$timestamp" <<'PY'
import sys
sys.path.insert(0, 'scripts')
import markdown_frontmatter
file_path, timestamp = sys.argv[1], sys.argv[2]
markdown_frontmatter.update(file_path, {'last_updated': timestamp})
print(f"  {file_path}.last_updated -> {timestamp}")
PY
}

function _sync_tracked_submodules() {
  local workdir="${SERVER_CONTEXT_WORKDIR:-$PWD}"
  SERVER_CONTEXT_WORKDIR="$workdir" bash "$workdir/scripts/setup/ensure_submodules.sh"
}

function _sync_external_dirs() {
  echo "[sync_external_dirs] Syncing external subdirectories..."
  sync_untracked "https://github.com/giladbarnea/llm-templates" "skills/prompt-subagent" ".agents/skills/prompt-subagent"
  echo "[sync_external_dirs] Sync complete."
}

# run_structural_maintenance [workdir=$PWD]
# The "public" function running idempotent structural maintenance tasks.
function run_structural_maintenance() {
  local workdir="${SERVER_CONTEXT_WORKDIR:-$PWD}"
  chmod +x .githooks/*
  _ensure_agent_symlinks "$workdir"
  _sync_tracked_submodules
  _generate_project_structure
  _sync_external_dirs
}
