#!/usr/bin/env bash
# Idempotently installs developer tooling: just (`just dev`) and gitleaks (pre-commit secret scan).
# Run in the background by setup.sh.
set -o pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_local_bin_path --quiet
ensure_just
ensure_gitleaks
