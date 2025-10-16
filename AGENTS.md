## Agents Guide

### Project overview (short)

- Purpose: Daily TLDR newsletter scraping/curation with a fast, distributed cache.
- Stack: Bash + curl, Python for scripting, Vercel Blob Store as the cache store.
- Vercel: Project uses Blob Store for all caching (newsletters, URL content, LLM summaries, scrape results). Reads via Blob Store base URL, writes via Python scripts using the `requests` library.
- Cache mechanism: Blob pathnames are deterministic based on content. 

### Environment variables

The single source of truth for what is available locally is the output of:

```bash
env | grep -e BLOB -e TLDR -e TOKEN -e API
```

**Run setup.sh first thing up load and verify your environment.**

Rules:

- **Local (Cursor background agents developing the app):** Env vars are prefixed with `TLDR_SCRAPER_` (except `OPENAI_API_TOKEN`, and `GITHUB_API_TOKEN`).
- **Production:** Exactly the same variables but without the `TLDR_SCRAPER_` prefix.

Expected variables (shown here with their base names; prefix with `TLDR_SCRAPER_` locally):

- `OPENAI_API_TOKEN`: `sk-...` (unprefixed in all environments)
- `GITHUB_API_TOKEN`: `github_pat_...` (unprefixed in all environments)
- `BLOB_STORE_BASE_URL`: read URL. Use e.g. `<BLOB_STORE_BASE_URL>/<pathname>`
- `BLOB_READ_WRITE_TOKEN`: `vercel_blob_rw_...`

### Common tasks and examples
#### Run serve.py locally

```bash
# Takes care of installing dependencies and bootstrapping the environment.
./setup.sh

uv run python3 serve.py
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

- Trust and Verify: Lean heavily on curling and running transient Python programs in a check-verify-trial-and-error process to make sure you know what you're doing, that you are expecting the right behavior, and to verify assumptions that any particular way of doing something is indeed the right way. This is doubly true when it comes to third-party integrations, third-party libraries, network requests, APIs, the existence and values of environment variables. 
- **Run ./setup.sh to verify the environment and dependencies are set up correctly. After sourcing setup.sh, run the CLI sanity check with `bash scripts/cli_sanity_check.sh` to verify all CLI commands are working properly.**
- Use `jq -S .` for sorted pretty-printing; `to_entries | length` for counts.
- Try the new feature or behavior you have just implemented in your shell. Is the app making a new API call? Add it to cli.py and scripts/cli_sanity_check.sh. New dependency and Python interface? Try it by running Python via uv, and so on.


### Development Conventions

1. Always use `util.resolve_env_var` to get environment variables.
2. Add a doctest example to pure-ish functions (data in, data out).
3. Do not abbreviate variable, function or class names. Use complete words. Write clean code.
4. `util.log` when something is going wrong, even if it is recoverable. Be consistent with existing logging style.
5. Failing early is better than fallbacks. Zero "Just in case" code. Fallback-rich code is to be avoided because it explodes complexity and often just propagates bugs downstream. Good code assumes that its inputs are valid and complete. It trusts upstream code to have done its job. And if something important fails, or an assumption is broken, fail early and clearly. Broken code should be fixed, not to tolerated, not worked around.
6. Make sure to write highly cohesive, decoupled logic.
7. Utilize existing logic when possible. Do not re-implement anything.
8. Write flat, optimized logical branches. Avoid nested, duplicate-y code. Write DRY and elegant logic.
9. Prefer `import modulename` and call `modulename.function()` rather than `from modulename import function`. Namespacing is an easy clarity win.

<Bad: fallback-rich, squirmy code>
@app.route("/api/summarize-url", methods=["POST"])
def summarize_url():
    """Requires 'url' in request body"""
    # Unnecessarily defends against broken upstream guarantees.
    data = request.get_json() or {}
    url = data.get("url", "")
    result = tldr_service.summarize_url_content(url) or ""
</Bad: fallback-rich, squirmy code>

<Good: straightforward, upstream-trusting code>
@app.route("/api/summarize-url", methods=["POST"])
def summarize_url():
    """Requires 'url' in request body"""
    # Assumes upstream guarantees are upheld (inputs are valid and complete) — thus keeps the state machine simpler.
    # If upstream guarantees are broken (e.g., missing 'url'), we WANT to fail as early as possible (in this case, `data['url']` will throw a KeyError)
    data = request.get_json()
    url = data['url']
    result = tldr_service.summarize_url_content(url)
</Good: straightforward, upstream-trusting code>

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

1. Know your weaknesses: your eagerness to solve a problem can cause tunnel vision. You may fix the issue but unintentionally create code duplication, deviate from the existing design, or introduce a regression in other coupled parts of the project you didn't consider. The solution is to literally look around beyond the immediate fix, be aware of (and account for) coupling around the codebase, integrate with the existing design, and periodically refactor.
2. You do your best work when you can verify yourself. With self-verification, you can and should practice continuous trial and error instead of a single shot in the dark.

### Feature Development Cycle

1. Source setup.sh, then run scripts/cli_sanity_check.sh. This will invoke cli.py, which is a CLI for the core business logic of the app.
2. Scan the files to understand the end-to-end dependency chain, call graphs, state mutations and assumptions. You must be aware of how your changes will affect components upstream and downstream.
3. Iteratively make your changes. Prefer to make bite-size changes that leave the app testable as a whole.
4. Generously run scripts/cli_sanity_check.sh and relevant cli.py commands  between changes to catch regressions early.
5. Once you're done, make sure cli.py is 100% aligned with serve.py and that scripts/cli_sanity_check.sh covers 100% of the functionality exposed in cli.py.
6. Verify your work by running the updated, now faithful scripts/cli_sanity_check.sh.