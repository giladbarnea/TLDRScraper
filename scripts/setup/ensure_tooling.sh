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

function install_gitleaks_binary(){
  local install_dir="$HOME/.local/bin"
  mkdir -p "$install_dir"

  local version
  version=$(curl -sS "https://api.github.com/repos/gitleaks/gitleaks/releases/latest" | grep -o '"tag_name": *"[^"]*"' | head -1 | cut -d'"' -f4)
  if [[ -z "$version" ]]; then
    error "Could not determine latest gitleaks version"
    return 1
  fi

  local os arch
  os=$(uname -s | tr '[:upper:]' '[:lower:]')
  arch=$(uname -m)
  [[ "$arch" == "x86_64" ]] && arch="x64"
  [[ "$arch" == "aarch64" ]] && arch="arm64"

  local filename="gitleaks_${version#v}_${os}_${arch}.tar.gz"
  local url="https://github.com/gitleaks/gitleaks/releases/download/${version}/${filename}"

  local tmp_dir
  tmp_dir=$(mktemp -d)
  trap "rm -rf '$tmp_dir'" EXIT

  if ! curl -sSfL "$url" -o "$tmp_dir/gitleaks.tar.gz"; then
    error "Failed to download gitleaks from $url"
    return 1
  fi

  if ! tar -xzf "$tmp_dir/gitleaks.tar.gz" -C "$tmp_dir"; then
    error "Failed to extract gitleaks"
    return 1
  fi

  if ! mv "$tmp_dir/gitleaks" "$install_dir/gitleaks"; then
    error "Failed to install gitleaks to $install_dir"
    return 1
  fi

  chmod +x "$install_dir/gitleaks"
  return 0
}

function ensure_gitleaks(){
  _ensure_tool gitleaks install_gitleaks_binary
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
