#!/usr/bin/env bash
# Background script: Install CLI tooling (gitleaks, etc.)
set -o pipefail

WORKDIR="${SERVER_CONTEXT_WORKDIR:-$PWD}"
SETUP_QUIET="${SETUP_QUIET:-false}"

source "$WORKDIR/scripts/setup/common.sh"

function ensure_local_bin_path(){
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

function _ensure_tool(){
  local tool="$1"
  local install_expression="$2"

  if command -v "$tool" 1>/dev/null 2>&1; then
    message "$tool is installed and in PATH"
    return 0
  fi

  message "$tool is not installed, installing with '$install_expression'"
  if ! eval "$install_expression" >/dev/null 2>&1; then
      error "Failed to install $tool."
      return 1
  fi

  if ! command -v "$tool" 1>/dev/null 2>&1; then
      error "After installing $tool, 'command -v $tool' returned a non-zero exit code. $tool is probably installed but not in PATH."
      return 1
  fi

  message "$tool installed and in the PATH"
  return 0
}

function ensure_gitleaks(){
  if isdefined apt; then
    _ensure_tool gitleaks "apt install -y gitleaks"
  else
    error "No supported package manager found (apt)"
    return 1
  fi
}

# Main execution
message "Starting tooling installation in background..."

ensure_local_bin_path

if ! ensure_gitleaks; then
    error "Failed to install gitleaks"
    exit 1
fi

message "Tooling installation complete"
exit 0
