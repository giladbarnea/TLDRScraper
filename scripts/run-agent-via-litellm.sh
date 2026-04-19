#!/usr/bin/env zsh
if [[ -z $(comm -12 <(pgrep -fai litellm | sort) <(lsof -ti:4000 | sort)) ]]; then
  kitty @ launch --cwd=$PWD --copy-env --title=litellm uvx --with='litellm[proxy]' --env-file=.env litellm --config=litellm_config.yaml
fi
env -u ANTHROPIC_API_KEY -u CLAUDECODE ANTHROPIC_BASE_URL="http://0.0.0.0:${proxy_port:-4000}" ANTHROPIC_AUTH_TOKEN="sk-1234" claude --dangerously-skip-permissions "$@"
