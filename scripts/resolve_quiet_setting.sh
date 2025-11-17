#!/usr/bin/env bash

# # should_be_quiet [-q,--quiet[=true|false]]
# Resolves the quiet setting from command line argument and environment variable SETUP_QUIET. CLI argument overrides environment variable.
# Returns 0 if quiet, 1 if not quiet.
# Usage: `if scripts/resolve_quiet_setting.sh "$1"; ...`
function should_be_quiet(){
	local quiet=false
	if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
			quiet=true
	elif [[ "$1" == "--quiet=true" ]]; then
			quiet=true
	elif [[ "$1" == "--quiet=false" ]]; then
			quiet=false
	fi

	# CLI argument overrides environment variable
	[[ "$1" != "--quiet=false" && "$SETUP_QUIET" == "true" ]] && quiet=true
	
	[[ "$quiet" == true ]]
}

should_be_quiet "$@"