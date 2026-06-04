#!/usr/bin/env bash
set -euo pipefail

cd /Users/giladbarnea/dev/TLDRScraper/experiments/liquid-glass/06-04-ios-weak-path-blur-gradient-specular
uv run -p python3 python3 -m http.server 8778 --bind 0.0.0.0 2>&1
