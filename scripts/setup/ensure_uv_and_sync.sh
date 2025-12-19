#!/usr/bin/env bash
# Background script: Install UV and sync Python dependencies
set -o pipefail

WORKDIR="${SERVER_CONTEXT_WORKDIR:-$PWD}"
QUIET="${SETUP_QUIET:-false}"

# Skip main execution when sourcing setup.sh
export SETUP_SH_SKIP_MAIN=1
source "$WORKDIR/setup.sh" || exit 1

function log() {
    [[ "$QUIET" != "true" ]] && echo "[uv-setup] $*" >&2
}

function error() {
    echo "[uv-setup] ERROR: $*" >&2
}

log "Starting UV installation and sync in background..."

# Ensure UV is installed
if ! ensure_uv --quiet="$QUIET"; then
    error "Failed to install UV"
    exit 1
fi

# Sync Python dependencies
if ! uv_sync --quiet="$QUIET"; then
    error "Failed to run uv sync"
    exit 1
fi

log "UV installation and sync complete"
exit 0
