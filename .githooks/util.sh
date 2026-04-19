#!/bin/bash

_HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_HOOKS_DIR/sync-external-subdir.sh"

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
		'.agents/agents'
		'.claude'
		'.pi'
		'.agents/skills/react-best-practices/rules'
		'.agents/skills/i-*'
		'.agents/skills/frontend-design-*'
		'.agents/skills/supabase-postgres-best-practices/*'
		'scripts/portfolio'
		'tests/'
		'thoughts/'
		
	)
	local ignore_glob
	local old_ifs="$IFS"
	IFS='|'
	ignore_glob="${ignore_glob_patterns[*]}"
	IFS="$old_ifs"
	local new_content
	new_content=$(uv run python3 scripts/generate_tree.py \
		--classify \
		--icons \
		--tree \
		--git-ignore \
		--all \
		--ignore-glob "$ignore_glob" \
		.)

	NEW_CONTENT="$new_content" uv run python3 - "PROJECT_STRUCTURE.md" "$(date -u +"%Y-%m-%d %H:%M")" <<'PY'
import sys, os
sys.path.insert(0, 'scripts')
import markdown_frontmatter
file_path, timestamp = sys.argv[1], sys.argv[2]
new_body = os.environ['NEW_CONTENT']
updated = markdown_frontmatter.update_if_body_changed(file_path, new_body, {'last_updated': timestamp})
print(f"  {file_path}.last_updated -> {timestamp}" if updated else f"  {file_path}: no content change, skipping")
PY
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
	local workdir="${SERVER_CONTEXT_WORKDIR:-$PWD}"
	local registry="$workdir/synced_external_subdirs.txt"
	echo "[sync_external_dirs] Syncing external subdirectories..."
	while IFS=' ' read -r repo_url src_dir dest_dir; do
		[[ -z "$repo_url" || "$repo_url" == "#"* ]] && continue
		sync_external_subdir "$repo_url" "$src_dir" "$dest_dir"
	done < "$registry"
	echo "[sync_external_dirs] Sync complete."
}

function _build_simplify_code_skill() {
  uv run python3 .agents/skills/simplify-code/build/build.py
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
  _build_simplify_code_skill
}
