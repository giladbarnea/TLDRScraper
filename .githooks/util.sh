#!/bin/bash

function generate_project_structure() {
	SETUP_QUIET=true SETUP_SH_SKIP_MAIN=1 source ./setup.sh
	_ignore_glob='.git|node_modules|__pycache__|*.pyc|.venv|static|*.vscode|*.cursor|experimental|thoughts/done|docs|.run'
	uv run python3 scripts/generate_tree.py \
		--classify \
		--icons \
		--tree \
		--git-ignore \
		--all \
		--ignore-glob "$_ignore_glob" \
		. > PROJECT_STRUCTURE.md
}