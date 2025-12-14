#!/bin/bash

function generate_project_structure() {
	SETUP_QUIET=true SETUP_SH_SKIP_MAIN=1 source ./setup.sh
	if ensure_eza --quiet; then
		_ignore_glob='.git|node_modules|__pycache__|*.pyc|.venv|static|*.vscode|*.cursor|experimental|thoughts/done|docs|.run'
		eza \
				--classify \
				--icons \
				--tree \
				--git-ignore \
				--all \
				--ignore-glob "$_ignore_glob" \
				. > PROJECT_STRUCTURE.md
	else
		# don't block the merge commit
		echo "[$0] ERROR: Failed to install eza, PROJECT_STRUCTURE.md not generated" >&2
	fi
}