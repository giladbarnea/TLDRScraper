#!/usr/bin/env bash
# Idempotently installs uv and syncs Python dependencies. Run in the background by setup.sh.
set -o pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_local_bin_path --quiet
uv_sync
