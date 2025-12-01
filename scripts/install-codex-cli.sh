#!/usr/bin/env bash

set -eo pipefail

npm install -g @openai/codex

printenv OPENAI_API_KEY | codex login --with-api-key


