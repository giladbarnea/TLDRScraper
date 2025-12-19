#!/usr/bin/env bash
# Background script: Build client dependencies
set -o pipefail

WORKDIR="${SERVER_CONTEXT_WORKDIR:-$PWD}"
QUIET="${SETUP_QUIET:-false}"

# Skip main execution when sourcing setup.sh
export SETUP_SH_SKIP_MAIN=1
source "$WORKDIR/setup.sh" || exit 1

function log() {
    [[ "$QUIET" != "true" ]] && echo "[client-build] $*" >&2
}

function error() {
    echo "[client-build] ERROR: $*" >&2
}

log "Starting client build in background..."

if ! build_client 1>/dev/null 2>&1; then
    error "Failed to build client"
    exit 1
fi

log "Client build complete"
exit 0
