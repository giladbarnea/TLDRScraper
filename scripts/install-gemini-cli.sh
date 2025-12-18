#!/usr/bin/env bash

set -e

npm install -g @google/gemini-cli

SETTINGS_TEMPLATE='{
  "general": {
    "previewFeatures": true,
    "retryFetchErrors": true
  },
  "context": {
    "fileName": [
      "AGENTS.md",
      "CLAUDE.md",
      "PROJECT_STRUCTURE.md",
      "ARCHITECTURE.md",
      "GEMINI.md"
    ],
    "includeDirectories": [
      "$HOME",
      "$CWD"
    ]
  },
  "experimental": {
    "codebaseInvestigatorSettings": {
      "enabled": true,
      "maxNumTurns": 20,
      "maxTimeMinutes": 10,
      "model": "gemini-3-pro-preview",
      "thinkingBudget": 32768
    }
  },
  "model": {
    "name": "gemini-3-pro-preview",
    "summarizeToolOutput": {
      "run_shell_command": {
        "tokenBudget": 5000
      }
    }
  },
  "security": {
    "auth": {
      "selectedType": "gemini-api-key"
    },
    "disableYoloMode": false
  },
  "tools": {
    "allowed": [
      "list_directory",
      "read_file",
      "write_file",
      "glob",
      "search_file_content",
      "replace",
      "run_shell_command",
      "web_fetch",
      "google_web_search",
      "save_memory",
      "write_todos"
    ],
    "autoAccept": true,
    "enableHooks": true,
    "sandbox": false
  },
  "useSmartEdit": true,
  "useWriteTodos": true
}'

mkdir -p "$HOME"/.gemini

echo "$SETTINGS_TEMPLATE" | jq --arg home "$HOME" --arg pwd "$PWD" '
  .context.includeDirectories = [
    $home,
    $pwd
  ]
' >"$HOME"/.gemini/settings.json

set -e
[[ -s "$HOME"/.gemini/settings.json ]]
set +e

