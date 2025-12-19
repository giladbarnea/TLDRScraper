#!/usr/bin/env bash
# Common utilities for setup scripts

isdefined(){
    command -v "$1" 1>/dev/null 2>&1
}

function message(){
	[[ "$SETUP_QUIET" != "true" ]] && echo "[$(basename "$0")] $*" >&2
	return 0
}

function error(){
  echo "[$(basename "$0")] ERROR: $*" >&2
}
