---
last_updated: 2026-04-04 07:39
---
# Pi + OpenRouter setup

Install Pi coding agent:

```bash
npm install -g @mariozechner/pi-coding-agent
pi --help
```

Confirm OpenRouter key is available:

```bash
env | rg '^OPENROUTER_API_KEY='
```

Use non-interactive print mode to verify one model:

```bash
pi --provider openrouter --model openrouter/auto -p "Reply with exactly: OK"
```

Run the multi-model smoke test:

```bash
./scripts/pi_openrouter_smoke.sh
```

Model mapping used in the smoke test:

- OpenRouter/auto → `openrouter/auto`
- Gemini 2.5 flash → `google/gemini-2.5-flash`
- Gemini 3 flash preview → `google/gemini-3-flash-preview`
- Gemini 3.1 pro preview → `google/gemini-3.1-pro-preview`
- glm-5 → `z-ai/glm-5`
- Minimax-2.5 → `minimax/minimax-m2.5`
- Minimax-2.7 → `minimax/minimax-m2.7`
- Gemma 4 "27B/30-something B" stretch models → `google/gemma-4-26b-a4b-it`, `google/gemma-4-31b-it`

If you prefer auth file-based credentials over env vars:

```json
{
  "openrouter": { "type": "api_key", "key": "OPENROUTER_API_KEY" }
}
```

Save that to `~/.pi/agent/auth.json`.
