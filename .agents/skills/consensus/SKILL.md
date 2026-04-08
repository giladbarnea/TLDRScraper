---
name: consensus
description: Run a no-web-server multi-model consensus loop (Claude + GPT + Gemini) for a prompt and use the converged answer in your response.
argument-hint: [question]
last_updated: 2026-04-08 07:16
---
# Consensus skill

Use this skill when the user asks you to arbitrate an answer across multiple models.

## What this does

- Runs a round-based consensus loop between Claude, GPT, and Gemini.
- Stops early when any model emits a `<conclusion>...</conclusion>` final answer.
- Otherwise returns a no-consensus fallback with each model's last response.

## Requirements

Set these environment variables:

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

Optional model overrides:

- `ANTHROPIC_MODEL`
- `OPENAI_MODEL`
- `GEMINI_MODEL`

## Run

```bash
uv run .agents/skills/consensus/scripts/run_consensus.py \
  "<question>" --thinking low --max-turns 4 --json
```

Use `--thinking high` for more expensive deeper reasoning.

## Agent workflow

1. Execute the script with the user's exact prompt.
2. Read the JSON output.
3. Use `answer` as the primary response, and mention if `reached_consensus` is false.
