## Agents Guide

### Project overview (short)

- Purpose: Daily TLDR newsletter scraping/curation with a tiny, fast cache.
- Stack: Bash + curl, Node/uv-Python for scripting, Vercel Edge Config as the cache store.
- Vercel: Project uses Edge Config `tldr-scraper-edge-config-store` under your team; reads via Edge Config connection string, writes via Vercel REST API.
- Cache mechanism: Keys are `{YYYY-MM-DD}-{type}`; values contain only `{ articles: [ { title, url } ] }`. A cache hit should return in tens of milliseconds due to Edge Config’s global distribution and low-latency reads.

### Environment variables

The single source of truth for what is available locally is the output of:

```bash
env | grep -e EDGE -e TLDR -e TOKEN -e API
```

Rules:

- **Local (Cursor background agents developing the app):** Env vars are prefixed with `TLDR_SCRAPER_` (except `VERCEL_TOKEN`).
- **Production:** Exactly the same variables but without the `TLDR_SCRAPER_` prefix (and `VERCEL_TOKEN` remains unprefixed).
- **Redundancy is intentional:** Both the full connection string and the decomposed parts exist so you never need to parse the connection string unless you want to.

Expected variables (shown here with their base names; prefix with `TLDR_SCRAPER_` locally):

- `EDGE_CONFIG_CONNECTION_STRING`: Full read URL, e.g. `https://edge-config.vercel.com/<EDGE_CONFIG_ID>?token=<EDGE_CONFIG_READ_TOKEN>`
- `EDGE_CONFIG_ID`: The `ecfg_...` identifier
- `EDGE_CONFIG_READ_TOKEN`: Read token for Edge Config
- `VERCEL_TOKEN`: Vercel API token used for write operations (unprefixed in all environments)
- `OPENAI_API_TOKEN`: Self explanatory.

Notes and examples:

- If you prefer parts over the full URL, you can construct the read URL yourself without parsing:
  ```bash
  READ_BASE="https://edge-config.vercel.com/${TLDR_SCRAPER_EDGE_CONFIG_ID}?token=${TLDR_SCRAPER_EDGE_CONFIG_READ_TOKEN}"
  ```

The code automatically looks (or at least _should_ automatically look) for both the prefixed and unprefixed forms.

### Common tasks and examples

- Read all items (read token):
```bash
curl -s -H "Authorization: Bearer $READ_TOKEN" \
  "https://edge-config.vercel.com/$EDGE_ID/items" | jq -S .
```

- Write items (API token + team scope) — batch upsert/delete:
```bash
curl -s -X PATCH \
  "https://api.vercel.com/v1/edge-config/$EDGE_ID/items" \
  -H "Authorization: Bearer $VERCEL_TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary @ops.json
```

- Payload shape for writes (works):
```json
{
  "items": [
    { "operation": "delete", "key": "old-key" },
    { "operation": "upsert", "key": "2025-09-20-ai", "value": { "articles": [ { "title": "...", "url": "..." } ] } }
  ]
}
```

### jq and uv setup

- Install jq (Linux x86_64):
```bash
mkdir -p "$HOME/.local/bin"
curl -fsSL -o "$HOME/.local/bin/jq" \
  "https://github.com/jqlang/jq/releases/download/jq-1.7.1/jq-linux-amd64"
chmod +x "$HOME/.local/bin/jq"
export PATH="$HOME/.local/bin:$PATH"
```

- Install uv and use Python via uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv --version
```

- Use Python through uv for quick scripts:
```bash
uv run python3 - <<'PY'
import json, sys
print("hello from uv python")
PY
```
- uv can transiently install dependencies if you need or consider integrating any:
```bash
uv run --with=dep1,dep2,dep3 python3 - <<'PY'
import dep1, dep2, dep3, os
dep1.do(os.environ["MY_API_KEY"])
PY
```

### Practical guidance

- Trust and Verify: Lean heavily on curling and running transient Python programs in a check-verify-trial-and-error process to make sure you know what you're doing, that you are expecting the right behavior, and to verify assumptions that any particular way of doing something is indeed the right way. This is doubly true when it comes to third-party integrations, third-party libraries, network requests, APIs, the existence and values of environment variables (`env|grep <wide queries>`)
- Use `jq -S .` for sorted pretty-printing; `to_entries | length` for counts.
- If you can emulate a new feature or behavior in your shell, do it. Is the app making a new API call? Try it in your shell. New dependency and Python interface? Try it by running Python via uv, and so on.
- Keys format: `{YYYY-MM-DD}-{type}`; only write keys for days that have articles. Do not write empty keys.
- Values should only contain:
  - `articles: [ { title, url }, ... ]`
  - Strip all `utm_*` query params before storing.
