#!/bin/bash

_HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_HOOKS_DIR/sync-subdir.sh"

function ensure_agent_symlinks() {
	local dot_dirs=(".claude" ".codex" ".gemini" ".pi")
	local workdir="${1:-${SERVER_CONTEXT_WORKDIR:-$PWD}}"

	for dir in "${dot_dirs[@]}"; do
		mkdir -p "$workdir/$dir"
		for target in "agents" "skills"; do
			local link_path="$workdir/$dir/$target"
			if [[ -L "$link_path" ]]; then
				local current_target
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

function generate_project_structure() {
	local workdir="${SERVER_CONTEXT_WORKDIR:-$PWD}"
	export PATH="${HOME}/.local/bin:${PATH}"
	ensure_agent_symlinks "$workdir"
	local ignore_glob='.git|node_modules|__pycache__|*.pyc|.venv|static|*.vscode|*.cursor|experimental|thoughts/done|docs|.run|.codex|.gemini|.claude/agents|.claude/skills|.pi/agents|.pi/skills|.agents/skills/react-best-practices/rules|.agents/skills/i-frontend-design/reference|.agents/skills/i-critique/reference'
	local target="PROJECT_STRUCTURE.md"
	local tmp; tmp=$(mktemp)
	uv run python3 scripts/generate_tree.py \
		--classify \
		--icons \
		--tree \
		--git-ignore \
		--all \
		--ignore-glob "$ignore_glob" \
		. > "$tmp"
	uv run python3 - "$target" "$tmp" <<'PY'
import sys, re
from pathlib import Path
target, tmp = Path(sys.argv[1]), Path(sys.argv[2])
tree = tmp.read_text()
frontmatter = ""
if target.exists():
    m = re.match(r'^---\s*\n.*?---\s*\n', target.read_text(), re.DOTALL)
    if m:
        frontmatter = m.group(0)
target.write_text(frontmatter + tree if frontmatter else tree)
PY
	rm "$tmp"
}

function sync_external_dirs() {
	echo "[sync_external_dirs] Syncing external subdirectories..."
	sync_untracked "https://github.com/giladbarnea/llm-templates" "skills/prompt-subagent" ".agents/skills/prompt-subagent"
	echo "[sync_external_dirs] Sync complete."
}
