#!/usr/bin/env bash
# Background script: Install Playwright browser/runtime dependencies
set -o pipefail

WORKDIR="${SERVER_CONTEXT_WORKDIR:-$PWD}"
SETUP_QUIET="${SETUP_QUIET:-false}"

source "$WORKDIR/scripts/setup/common.sh"

function ensure_local_bin_path() {
  if [[ -d "/home/ubuntu" ]]; then
    if [[ ":$PATH:" != *":/home/ubuntu/.local/bin:"* ]]; then
      export PATH="/home/ubuntu/.local/bin:$PATH"
    fi
    return 0
  fi

  if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    mkdir -p "$HOME/.local/bin"
    export PATH="$HOME/.local/bin:$PATH"
  fi
}

function _ensure_tool() {
  local tool="$1"
  local install_expression="$2"

  if isdefined "$tool"; then
    message "$tool is installed and in PATH"
    return 0
  fi

  message "$tool is not installed, installing with '$install_expression'"
  if ! eval "$install_expression" >/dev/null 2>&1; then
    error "Failed to install $tool."
    return 1
  fi

  if ! isdefined "$tool"; then
    error "After installing $tool, 'command -v $tool' returned a non-zero exit code. $tool is probably installed but not in PATH."
    return 1
  fi

  message "$tool installed and in the PATH"
  return 0
}

function ensure_uv() {
  _ensure_tool uv "curl -LsSf https://astral.sh/uv/install.sh | sh"
}

function ensure_playwright_chromium() {
  message "Installing Playwright Chromium browser and host dependencies..."
  if ! uv run playwright install --with-deps chromium >/dev/null 2>&1; then
    error "Failed to install Playwright Chromium browser/dependencies"
    return 1
  fi
  message "Playwright Chromium browser/dependencies installed"
  return 0
}

message "Starting Playwright installation..."

ensure_local_bin_path

if ! ensure_uv; then
  error "Failed to install UV"
  exit 1
fi

if ! ensure_playwright_chromium; then
  error "Failed to install Playwright Chromium browser/dependencies"
  exit 1
fi

message "Playwright installation complete"
exit 0
