#!/usr/bin/env bash
# Background script: Build client dependencies
set -o pipefail

WORKDIR="${SERVER_CONTEXT_WORKDIR:-$PWD}"
SETUP_QUIET="${SETUP_QUIET:-false}"

source "$WORKDIR/scripts/setup/common.sh"

# build_client
function build_client(){
  if { builtin cd "$WORKDIR/client" && npm ci && npm run build; } then
    message "Successfully built client"
    builtin cd "$WORKDIR"
    return 0
  else
    error "Failed to 'cd client && npm ci && npm run build'"
    builtin cd "$WORKDIR"
    return 1
  fi
}

# Main execution
message "Starting client build in background..."

if ! build_client 1>/dev/null 2>&1; then
    error "Failed to build client"
    exit 1
fi

message "Client build complete"
exit 0
