#!/usr/bin/env bash
# Background script: Install UV and sync Python dependencies
set -o pipefail

WORKDIR="${SERVER_CONTEXT_WORKDIR:-$PWD}"
SETUP_QUIET="${SETUP_QUIET:-false}"

source "$WORKDIR/scripts/setup/common.sh"

# ensure_local_bin_path
function ensure_local_bin_path(){
    # Cursor web agent installs to /home/ubuntu/.local/bin.
    if [[ -d "/home/ubuntu" ]]; then
        if [[ ":$PATH:" != *":/home/ubuntu/.local/bin:"* ]]; then
            export PATH="/home/ubuntu/.local/bin:$PATH"
        fi
        return 0
    fi

    # The default path for local bin is $HOME/.local/bin.
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        mkdir -p "$HOME/.local/bin"
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

# _ensure_tool <TOOL> <INSTALL_EXPRESSION>
function _ensure_tool(){
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

# ensure_uv
function ensure_uv(){
  _ensure_tool uv "curl -LsSf https://astral.sh/uv/install.sh | sh"
}

# uv_sync
function uv_sync(){
    ensure_uv || return 1
    message "Running 'uv sync'..."
    local uv_sync_output
    if uv_sync_output=$(uv sync -p 3.11 2>&1); then
        message "Successfully ran uv sync. Use 'uv run python3 ...' to run Python."
        return 0
    else
        error "failed to uv sync. Output:"
        echo "$uv_sync_output" >&2
        return 1
    fi
}

# Main execution
message "Starting UV installation and sync in background..."

ensure_local_bin_path

if ! ensure_uv; then
    error "Failed to install UV"
    exit 1
fi

if ! uv_sync; then
    error "Failed to run uv sync"
    exit 1
fi

message "UV installation and sync complete"
exit 0
