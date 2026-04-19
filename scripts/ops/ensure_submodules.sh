#!/usr/bin/env bash
# Idempotently materialize tracked git submodules for local dev, CI, and production builds.
set -o pipefail

WORKDIR="${SERVER_CONTEXT_WORKDIR:-$PWD}"
SETUP_QUIET="${SETUP_QUIET:-false}"

source "$WORKDIR/scripts/env/common.sh"

function ensure_tracked_submodules() {
  local repo_root=""

  if repo_root="$(git -C "$WORKDIR" rev-parse --show-toplevel 2>/dev/null)"; then
    :
  elif [[ -d "$WORKDIR/vendor/consensus" ]]; then
    message "Git metadata unavailable, but vendored submodules already exist"
    return 0
  else
    error "Git metadata unavailable and tracked submodules are missing"
    return 1
  fi

  if [[ ! -f "$repo_root/.gitmodules" ]]; then
    message "No .gitmodules file found, skipping tracked submodule sync"
    return 0
  fi

  if ! git -C "$repo_root" config -f .gitmodules --name-only --get-regexp '^submodule\..*\.path$' >/dev/null 2>&1; then
    message "No tracked submodules declared, skipping tracked submodule sync"
    return 0
  fi

  message "Syncing tracked git submodules..."
  if ! git -C "$repo_root" submodule sync --recursive; then
    error "Failed to sync tracked git submodules"
    return 1
  fi

  if ! git -C "$repo_root" -c protocol.file.allow=always submodule update --init --recursive; then
    error "Failed to initialize tracked git submodules"
    return 1
  fi

  message "Tracked git submodules are ready"
  return 0
}

ensure_tracked_submodules || exit 1
