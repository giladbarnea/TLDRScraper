#!/usr/bin/env bash
# Idempotently installs client dependencies and builds the client. Run in the background by setup.sh.
set -o pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_local_bin_path --quiet
build_client
