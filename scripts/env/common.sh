#!/usr/bin/env bash
# SOURCE this file, don't run it.
# Common utilities shared by setup.sh and the scripts/env/*.sh background installers.

# common.sh lives in scripts/env/; the repo root is two levels up. Derive it once so
# every consumer (setup.sh or a standalone background script) has a sane workdir.
export SERVER_CONTEXT_WORKDIR="${SERVER_CONTEXT_WORKDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# message <TEXT...>
# Writes an informational message to stderr unless SETUP_QUIET is enabled.
# setup.sh overrides this with its own "[setup.sh]"-prefixed version.
function message() {
  [[ "${SETUP_QUIET:-false}" == "true" ]] && return 0
  echo "$*" >&2
  return 0
}

# error <TEXT...>
# Writes an error message to stderr. setup.sh overrides this for its own context.
function error() {
  echo "ERROR: $*" >&2
}

# isdefined <NAME>
# True if NAME resolves to an available command, function, builtin, or alias.
function isdefined() {
  command -v "$1" >/dev/null 2>&1
}

decolor() {
  local text="${1:-$(cat /dev/stdin)}"
  # Remove ANSI color codes step by step using basic bash parameter expansion
  # Remove escape sequences like \033[0m, \033[31m, \033[1;31m, etc.

  # Remove \033[*m patterns (any characters between [ and m)
  while [[ "$text" == *$'\033['*m* ]]; do
    text="${text//$'\033['*m/}"
  done

  # Also handle \e[*m patterns (alternative escape sequence format)
  while [[ "$text" == *$'\e['*m* ]]; do
    text="${text//$'\e['*m/}"
  done

  echo -n "$text"
}

# ensure_local_bin_path [-q,--quiet]
# Idempotently ensures the local bin directory is on PATH.
function ensure_local_bin_path() {
  local quiet="${1:-false}"
  [[ "$SETUP_QUIET" == "true" ]] && quiet=true

  # Cursor web agent installs to /home/ubuntu/.local/bin.
  if [[ -d "/home/ubuntu" ]]; then
    if [[ ":$PATH:" == *":/home/ubuntu/.local/bin:"* ]]; then
      [[ "$quiet" == false ]] && message "[$0] /home/ubuntu/.local/bin already present in PATH"
      return 0
    fi
    export PATH="/home/ubuntu/.local/bin:$PATH"
    [[ "$quiet" == false ]] && message "[$0] Added /home/ubuntu/.local/bin to PATH"
    return 0
  fi

  # The default path for local bin is $HOME/.local/bin.
  if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
    [[ "$quiet" == false ]] && message "[$0] \$HOME/.local/bin already present in PATH"
    return 0
  fi
  mkdir -p "$HOME/.local/bin"
  export PATH="$HOME/.local/bin:$PATH"
  [[ "$quiet" == false ]] && message "[$0] Added \$HOME/.local/bin to PATH"
}

# _ensure_tool [-q,-quiet] <TOOL> <INSTALL_EXPRESSION>
# Private function: idempotent installation of TOOL.
function _ensure_tool() {
  local quiet=false
  local tool=""
  local install_expression=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
    --quiet)
      if [[ "$2" != false && "$2" != true ]]; then
        quiet=true
      else
        quiet="$2"
        shift
      fi
      ;;
    --quiet=false)
      quiet=false
      ;;
    --quiet=true)
      quiet=true
      ;;
    -q)
      quiet=true
      ;;
    *)
      tool="$1"
      install_expression="$2"
      shift
      ;;
    esac
    shift
  done
  [[ "$SETUP_QUIET" == "true" ]] && quiet=true
  local _self_name="ensure_$tool"
  if isdefined "$tool"; then
    [[ "$quiet" == false ]] && message "[$_self_name] $tool is installed and in PATH"
    return 0
  fi
  [[ "$quiet" == false ]] && message "[$_self_name] $tool is not installed, installing with '$install_expression'" >&2
  if ! eval "$install_expression" >/dev/null 2>&1; then
    message "[$_self_name] ERROR: Failed to install $tool." >&2
    return 1
  fi
  if ! isdefined "$tool"; then
    message "[$_self_name] ERROR: After installing $tool, 'command -v $tool' returned a non-zero exit code. $tool is probably installed but not in PATH." >&2
    return 1
  fi
  [[ "$quiet" == false ]] && message "[$_self_name] $tool installed and in the PATH"
  return 0
}

# ensure_uv [-q,-quiet]
# Idempotent installation of uv.
function ensure_uv() {
  _ensure_tool uv "curl -LsSf https://astral.sh/uv/install.sh | sh" "$@"
}

# ensure_just [-q,-quiet]
# Idempotent installation of just (the command runner used by `just dev`).
function ensure_just() {
  local version="1.36.0"
  local url="https://github.com/casey/just/releases/download/${version}/just-${version}-$(uname -m)-unknown-linux-musl.tar.gz"
  _ensure_tool just "curl -sSfL '$url' | tar -xz -C \"\$HOME/.local/bin\" just" "$@"
}

# ensure_gitleaks [-q,-quiet]
# Idempotent installation of gitleaks (the pre-commit secret scanner).
function ensure_gitleaks() {
  local operating_system architecture
  operating_system="$(uname -s | tr '[:upper:]' '[:lower:]')"
  case "$(uname -m)" in
  x86_64 | amd64) architecture=x64 ;;
  aarch64 | arm64) architecture=arm64 ;;
  *) architecture=x64 ;;
  esac
  local version="8.21.2"
  local url="https://github.com/gitleaks/gitleaks/releases/download/v${version}/gitleaks_${version}_${operating_system}_${architecture}.tar.gz"
  _ensure_tool gitleaks "curl -sSfL '$url' | tar -xz -C \"\$HOME/.local/bin\" gitleaks" "$@"
}

# uv_sync [-q,-quiet]
# Idempotent installation of Python dependencies using uv.
function uv_sync() {
  local quiet=false
  if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
    quiet=true
  elif [[ "$1" == "--quiet=true" ]]; then
    quiet=true
  elif [[ "$1" == "--quiet=false" ]]; then
    quiet=false
  fi
  [[ "$SETUP_QUIET" == "true" ]] && quiet=true
  ensure_uv --quiet || return 1
  [[ "$quiet" == false ]] && message "[$0] Running 'uv sync'..."
  local uv_sync_output
  if uv_sync_output=$(uv sync -p 3.11 2>&1); then
    [[ "$quiet" == false ]] && message "[$0] Successfully ran uv sync. Use 'uv run python3 ...' to run Python."
    return 0
  else
    error "[$0] failed to uv sync. Output:"
    echo "$uv_sync_output" >&2
    return 1
  fi
}

function build_client() {
  if { builtin cd "$SERVER_CONTEXT_WORKDIR/client" && npm ci && npm run build; }; then
    message "[$0] Successfully built client"
    builtin cd "$SERVER_CONTEXT_WORKDIR"
    return 0
  else
    message "[$0][ERROR] Failed to 'cd client && npm ci && npm run build'" >&2
    builtin cd "$SERVER_CONTEXT_WORKDIR"
    return 1
  fi
}
