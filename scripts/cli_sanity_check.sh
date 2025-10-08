#!/usr/bin/env bash
set -euo pipefail

# Simple happy-path sanity check for the TLDR CLI. The script invokes
# each CLI command that mirrors the public HTTP endpoints and performs
# basic assertions on the responses. It also verifies that removing a
# URL persists the canonical URL in the removed cache and that
# summarizing a URL materializes the summary in cache for cache-only
# reads.

source ./scripts/background-agent-setup.sh

CLI_BIN=${CLI_BIN:-"uv run python3 cli.py"}
SCRAPE_START_DATE=${SCRAPE_START_DATE:-$(date -I -d 'yesterday' 2>/dev/null || date -I)}
SCRAPE_END_DATE=${SCRAPE_END_DATE:-$SCRAPE_START_DATE}
SUMMARY_URL=${SUMMARY_URL:-"https://example.com/"}
SUMMARY_EFFORT=${SUMMARY_EFFORT:-"low"}
REMOVAL_URL=${REMOVAL_URL:-"https://example.com/removed"}
INVALIDATE_START_DATE=${INVALIDATE_START_DATE:-$SCRAPE_START_DATE}
INVALIDATE_END_DATE=${INVALIDATE_END_DATE:-$SCRAPE_END_DATE}
INVALIDATE_DATE=${INVALIDATE_DATE:-$SCRAPE_START_DATE}

SCRAPE_COMMAND=${SCRAPE_COMMAND:-scrape}
PROMPT_COMMAND=${PROMPT_COMMAND:-prompt}
SUMMARIZE_COMMAND=${SUMMARIZE_COMMAND:-summarize-url}
REMOVE_COMMAND=${REMOVE_COMMAND:-remove-url}
REMOVED_LIST_COMMAND=${REMOVED_LIST_COMMAND:-removed-urls}
CACHE_MODE_COMMAND=${CACHE_MODE_COMMAND:-cache-mode}
INVALIDATE_RANGE_COMMAND=${INVALIDATE_RANGE_COMMAND:-invalidate-cache}
INVALIDATE_DATE_COMMAND=${INVALIDATE_DATE_COMMAND:-invalidate-date-cache}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

log() {
    printf '[cli-sanity] %s\n' "$*"
}

read -r -a CLI_COMMAND <<<"$CLI_BIN"

run_cli_capture() {
    local stdout_file="$TMP_DIR/stdout_${COMMAND_INDEX}"
    local stderr_file="$TMP_DIR/stderr_${COMMAND_INDEX}"
    COMMAND_INDEX=$((COMMAND_INDEX + 1))

    log "Running: $CLI_BIN $*" >&2

    if ! "${CLI_COMMAND[@]}" "$@" >"$stdout_file" 2>"$stderr_file"; then
        if [[ -s "$stderr_file" ]]; then
            sed 's/^/[cli stderr] /' "$stderr_file" >&2
        fi
        if [[ -s "$stdout_file" ]]; then
            sed 's/^/[cli stdout] /' "$stdout_file" >&2
        fi
        exit 1
    fi

    if [[ -s "$stderr_file" ]]; then
        sed 's/^/[cli stderr] /' "$stderr_file" >&2
    fi

    cat "$stdout_file"
}

require_command jq
require_command uv

TMP_DIR=$(mktemp -d)
COMMAND_INDEX=0
trap 'rm -rf "$TMP_DIR"' EXIT

# Ensure the CLI advertises the expected commands.
log "Discovering CLI commands"
CLI_HELP=$(run_cli_capture --help)
for subcommand in "$SCRAPE_COMMAND" "$SUMMARIZE_COMMAND" "$PROMPT_COMMAND" "$REMOVE_COMMAND" "$REMOVED_LIST_COMMAND" "$CACHE_MODE_COMMAND" "$INVALIDATE_RANGE_COMMAND" "$INVALIDATE_DATE_COMMAND"; do
    if ! grep -Eq "^[[:space:]]*$subcommand(\s|$)" <<<"$CLI_HELP"; then
        echo "Required CLI subcommand '$subcommand' not found in help output" >&2
        exit 1
    fi
done

# Scrape endpoint
SCRAPE_JSON=$(run_cli_capture "$SCRAPE_COMMAND" --start-date "$SCRAPE_START_DATE" --end-date "$SCRAPE_END_DATE")
log "Scrape response: $SCRAPE_JSON"
echo "$SCRAPE_JSON" | jq -e '.success == true' >/dev/null

# Prompt endpoint
PROMPT_OUTPUT=$(run_cli_capture "$PROMPT_COMMAND")
if [[ -z ${PROMPT_OUTPUT//[[:space:]]/} ]]; then
    echo "Prompt output was empty" >&2
    exit 1
fi

# Cache mode (GET then set back to reported value)
CACHE_MODE_JSON=$(run_cli_capture "$CACHE_MODE_COMMAND" get)
CACHE_MODE=$(echo "$CACHE_MODE_JSON" | jq -r '.cache_mode // empty')
if [[ -z "$CACHE_MODE" ]]; then
    echo "Failed to resolve cache mode from response: $CACHE_MODE_JSON" >&2
    exit 1
fi
log "Cache mode currently: $CACHE_MODE"
CACHE_MODE_SET_HELP=$(run_cli_capture "$CACHE_MODE_COMMAND" set --help || true)
if grep -q -- '--cache-mode' <<<"$CACHE_MODE_SET_HELP"; then
    CACHE_MODE_SET_JSON=$(run_cli_capture "$CACHE_MODE_COMMAND" set --cache-mode "$CACHE_MODE")
else
    CACHE_MODE_SET_JSON=$(run_cli_capture "$CACHE_MODE_COMMAND" set --mode "$CACHE_MODE")
fi
echo "$CACHE_MODE_SET_JSON" | jq -e '.success == true' >/dev/null

# Invalidate range endpoint
INVALIDATE_RANGE_JSON=$(run_cli_capture "$INVALIDATE_RANGE_COMMAND" --start-date "$INVALIDATE_START_DATE" --end-date "$INVALIDATE_END_DATE")
echo "$INVALIDATE_RANGE_JSON" | jq -e '.success == true' >/dev/null

# Invalidate single date endpoint
INVALIDATE_DATE_JSON=$(run_cli_capture "$INVALIDATE_DATE_COMMAND" --date "$INVALIDATE_DATE")
echo "$INVALIDATE_DATE_JSON" | jq -e '.success == true' >/dev/null

# Summarize URL and confirm cache-only retrieval works afterwards
SUMMARY_JSON=$(run_cli_capture "$SUMMARIZE_COMMAND" --url "$SUMMARY_URL" --summary-effort "$SUMMARY_EFFORT")
echo "$SUMMARY_JSON" | jq -e '.success == true' >/dev/null
SUMMARY_PATH=$(echo "$SUMMARY_JSON" | jq -r '.summary_blob_pathname // empty')
if [[ -z "$SUMMARY_PATH" ]]; then
    echo "Summarize command did not return a blob pathname" >&2
    exit 1
fi

SUMMARY_CACHE_JSON=$(run_cli_capture "$SUMMARIZE_COMMAND" --url "$SUMMARY_URL" --summary-effort "$SUMMARY_EFFORT" --cache-only)
echo "$SUMMARY_CACHE_JSON" | jq -e '.success == true' >/dev/null
SUMMARY_CACHE_PATH=$(echo "$SUMMARY_CACHE_JSON" | jq -r '.summary_blob_pathname // empty')
if [[ "$SUMMARY_CACHE_PATH" != "$SUMMARY_PATH" ]]; then
    echo "Cache-only summarize returned a different blob pathname" >&2
    exit 1
fi

# Remove URL and verify canonical URL recorded in removed cache via CLI
REMOVE_JSON=$(run_cli_capture "$REMOVE_COMMAND" --url "$REMOVAL_URL")
echo "$REMOVE_JSON" | jq -e '.success == true' >/dev/null
CANONICAL_REMOVAL_URL=$(uv run python3 -c "
import sys
import util
print(util.canonicalize_url('$REMOVAL_URL'))
")

REMOVED_LIST_JSON=$(run_cli_capture "$REMOVED_LIST_COMMAND")
if echo "$REMOVED_LIST_JSON" | jq -e --arg url "$CANONICAL_REMOVAL_URL" '
    if type == "array" then index($url) != null
    elif type == "object" then ((.removed_urls // []) + (.urls // []) + (.data // [])) | index($url) != null
    else false end
' >/dev/null 2>&1; then
    :
else
    echo "Removed URLs response does not contain $CANONICAL_REMOVAL_URL: $REMOVED_LIST_JSON" >&2
    exit 1
fi

log "CLI sanity check completed successfully"
