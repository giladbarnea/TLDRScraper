## Agents Guide

### Project overview (short)

- Purpose: Daily TLDR newsletter scraping/curation with a tiny, fast cache.
- Stack: Bash + curl, Node/uv-Python for scripting, Vercel Edge Config as the cache store.
- Vercel: Project uses Edge Config `tldr-scraper-edge-config-store` under your team; reads via Edge Config connection string, writes via Vercel REST API. WIP: Blob store for caching fetched web pages contents and LLM summaries.
- URLs Cache mechanism: Keys are `{YYYY-MM-DD}-{type}`; values contain only `{ articles: [ { title, url } ] }`. A cache hit should return in tens of milliseconds due to Edge Config’s global distribution and low-latency reads.

**ATTENTION:**: Edge Config is awaiting deprecation. The project will be migrated to Blob store only. Avoid utilizing Edge Config for new features.

### Environment variables

The single source of truth for what is available locally is the output of:

```bash
env | grep -e EDGE -e BLOB -e TLDR -e TOKEN -e API
```

Rules:

- **Local (Cursor background agents developing the app):** Env vars are prefixed with `TLDR_SCRAPER_` (except `VERCEL_TOKEN` and `GITHUB_API_TOKEN`).
- **Production:** Exactly the same variables but without the `TLDR_SCRAPER_` prefix (and `VERCEL_TOKEN` remains unprefixed).
- **Redundancy is intentional:** Both the full connection string and the decomposed parts exist so you never need to parse the connection string unless you want to.

Expected variables (shown here with their base names; prefix with `TLDR_SCRAPER_` locally):

- `OPENAI_API_TOKEN`: `sk-...` (unprefixed in all environments)
- `VERCEL_TOKEN`: Vercel API token used for write operations (unprefixed in all environments)
- `GITHUB_API_TOKEN`: `github_pat_...` (unprefixed in all environments)
- `EDGE_CONFIG_CONNECTION_STRING`: Full read URL, e.g. `https://edge-config.vercel.com/<EDGE_CONFIG_ID>?token=<EDGE_CONFIG_READ_TOKEN>`
- `EDGE_CONFIG_READ_TOKEN`: Read token for Edge Config
- `EDGE_CONFIG_ID`: The `ecfg_...` identifier
- `BLOB_STORE_BASE_URL`: read URL. Use e.g. `<BLOB_STORE_BASE_URL>/<pathname>`
- `BLOB_READ_WRITE_TOKEN`: `vercel_blob_rw_...`

### Common tasks and examples
#### Run serve.py locally

```bash
# Takes care of installing dependencies and bootstrapping the environment.
./scripts/background-agent-setup.sh

# .env should be already populated by the setup script.
uv run --env-file=./.env python3 serve.py
```

#### Vercel CLI (required for Blob uploads from Python)
Install once:
```bash
npm i -g vercel
vercel --help
```
The server shells out to:
```bash
vercel blob put <tmpfile> --pathname "<normalized-pathname>" --force --token "$BLOB_READ_WRITE_TOKEN"
```
Upload is deterministic and overwrites existing content at the same pathname (no random suffixes, no listing).

- Payload shape for writes:
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
source setup.sh
ensure_uv
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
  * `articles: [ { title, url }, ... ]`
  * Strip all `utm_*` query params before storing.
- Failing early is better than fallbacks. Zero “Just in case” code. Fallback-rich code explodes complexity and often just propagates bugs downstream. If something important fails, fail early and clearly. Broken code should be fixed, not worked around.

### Development Conventions

- Always use `util.resolve_env_var` to get environment variables.
- Add a doctest example to pure-ish functions (data in, data out).
- Do not abbreviate variable, function or class names. Use complete words.
- `util.log` when something is going wrong, even if it is recoverable. Be consistent with existing logging style.

### The Right Engineering Mindset

1. Increasing complexity is detrimental. Each new function or logical branch adds to this complexity. In your decision-making, try to think of ways to reduce complexity, rather than just to solve the immediate problem ad-hoc. Sometimes reducing complexity requires removing code, which is OK. If done right, removing code is beneficial similarly to how clearing Tetris blocks is beneficial — it simplifies and creates more space.
2. Prefer declarative approaches. People understand things better when they can see the full picture instead of having to dive in. Difficulty arises when flow and logic are embedded implicitly in a sprawling implementation.
3. Avoid over-engineering and excessive abstraction. Code is ephemeral. Simplicity and clarity are key to success.
4. If you're unsure whether your response is correct, that's completely fine—just let me know of your uncertainty and continue responding. We're a team.
5. Do not write comments in code, unless they are critical for understanding. Especially, do not write "breadcrumb" comments saying "modified: foo" or "added: bar", as if to leave a modification trail behind.
6. For simple tasks that could be performed straight away, do not think much. Just do it. For more complex tasks that would benefit from thinking, think deeper, proportionally to the task's complexity. Regardless, always present your final response in a direct and concise manner. No fluff.
7. Do NOT fix linter errors unless instructed by the user to do so.
8. Docstrings should be few and far between. When you do write one, keep it to 1-2 sentences max.

### Crucial Important Rules
1. When asked to implement a feature, first plan it.
2. When asked to fix a problem, first think and explore until you understand the "moving parts" related to the hypothesized root cause — the dependencies and dependents around the codebase. This helps you pin down the actual root cause rather than applying band aids. Then plan your fix step-by-step before changing files or writing code.
**Important**: For each planned step, identify and clearly lay out the logical dependencies of that change, as well as potentially affected logical dependents. This ensures you uncover coupling between components and implicit dependencies, which is absolutely necessary for avoiding bugs.
3. When making changes, be absolutely SURGICAL. Every line of code you add incurs a small debt; this debt compounds over time through maintenance costs, potential bugs, and cognitive load for everyone who must understand it later. Therefore, make only laser-focused changes, executing exactly what the user required — no less, no more.
4. No band-aid fixes. When encountering a problem, first brainstorm what possible root causes may explain it. band-aid fixes are bad because they increase complexity significantly. Root-cause solutions are good because they reduce complexity.

### Being an Effective AI Agent

1. Know your weaknesses: your eagerness to solve a problem can cause tunnel vision. You may fix the issue but unintentionally create code duplication, deviate from the existing design, or introduce a regression in other coupled parts of the project you didn’t consider. The solution is to literally look around beyond the immediate fix, be aware of (and account for) coupling around the codebase, integrate with the existing design, and periodically refactor.
2. You do your best work when you can verify yourself. With self-verification, you can and should practice continuous trial and error instead of a single shot in the dark.