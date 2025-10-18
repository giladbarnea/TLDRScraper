#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export WORKDIR="${WORKDIR:-$PROJECT_ROOT}"

SETUP_SH_SKIP_MAIN=1 source "$PROJECT_ROOT/setup.sh"
watchdog "$@"
