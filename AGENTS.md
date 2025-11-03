---
last-updated: 2025-11-03 23:10, 102a8dc
---
# Agents Guide

## Project overview

Newsletter aggregator that scrapes tech newsletters from multiple sources, displays them in a unified interface, and provides AI-powered summaries and TLDRs.

- Stack: 
   * Python: Flask backend, serverless on Vercel
   * React 19 + Vite (frontend) (in `client/`)
   * Client-side localStorage for all caching
   * OpenAI GPT-5 for summaries and TLDRs
- Storage: Project uses browser localStorage for all caching (newsletters, URL content, LLM summaries, scrape results). All data persistence happens in the browser.
- Cache mechanism: localStorage keys follow deterministic patterns based on content and dates. 

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed flows & user interactions documentation and [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for a map of the project structure.

## Environment variables

The single source of truth for what is available locally is the output of:

```bash
env | grep -e TLDR -e TOKEN -e API -e KEY
```

**Run setup.sh first thing up load and verify your environment.**

Rules:

- **Local (Cursor background agents developing the app):** Env vars are prefixed with `TLDR_SCRAPER_` (except `OPENAI_API_KEY`, and `GITHUB_API_TOKEN`).
- **Production:** Exactly the same variables but without the `TLDR_SCRAPER_` prefix.

Expected variables (shown here with their base names; prefix with `TLDR_SCRAPER_` locally):

- `OPENAI_API_KEY`: `sk-...` (unprefixed in all environments)
- `GITHUB_API_TOKEN`: `github_pat_...` (unprefixed in all environments)
- `FIRECRAWL_API_KEY`: `fc_...` (unprefixed in all environments)

## Development & Setup

### Running the server and logs watchdog
```bash
# Verify the environment and dependencies are set up correctly.
source ./setup.sh

# Start the server and watchdog in the background. Logs output to file.
start_server_and_watchdog

# Verify the server is running.
print_server_and_watchdog_pids

# Exercise the API with curl requests.
curl http://localhost:5001/api/scrape
curl http://localhost:5001/api/summarize-url
curl http://localhost:5001/api/tldr-url
curl ...additional endpoints that may be relevant...

# Stop the server and watchdog.
kill_server_and_watchdog
```


## Client setup

```bash
cd client
npm install
npm run build
```

### Frontend development mode

For frontend development with hot reload:

```bash
cd client
npm run dev
```

This runs Vite dev server on port 3000 with API proxy to localhost:5001.


### `uv` installation and usage

- Install `uv` and use Python via `uv`:
```bash
source setup.sh
ensure_uv
uv --version
```

- Use Python via `uv` for quick testing:
```bash
uv run python3 - <<'PY'
import json, sys
print("hello from uv python")
PY
```
- `uv` can transiently install dependencies if you need or consider integrating any:
```bash
uv run --with=dep1,dep2,dep3 python3 - <<'PY'
import dep1, dep2, dep3, os
dep1.do(os.environ["MY_API_KEY"])
PY
```

## YOU MUST **FULLY** READ **ALL MARKDOWN FILES IN THE ROOT DIRECTORY** BEFORE DOING ANYTHING ELSE.

The markdown docs at the project's root contain crucial information. Read them fully. Studying and internalizing them is essential for you to complete a task successfully and efficiently.

This includes, but is not limited to:
1. PROJECT_STRUCTURE.md
2. ARCHITECTURE.md
3. GOTCHAS.md

## Practical guidance

- Trust and Verify: Lean heavily on curling and running transient Python programs in a check-verify-trial-and-error process to make sure you know what you're doing, that you are expecting the right behavior, and to verify assumptions that any particular way of doing something is indeed the right way. This is doubly true when it comes to third-party integrations, third-party libraries, network requests, APIs, the existence and values of environment variables. 
- **Run `source ./setup.sh` to verify the environment and dependencies are set up correctly. After sourcing it, use `start_server_and_watchdog` and `print_server_and_watchdog_pids` to confirm the local server is running. Generously exercise the API with `curl` requests (e.g., `/api/scrape`, `/api/summarize-url`, `/api/tldr-url`) throughout the development process to catch regressions early. Use `kill_server_and_watchdog` for cleanup.**
- Verify every new behavior, fix or modification you make by utilizing your shell. If possible, execute the modified flow to ensure nothing is broken.


## Development Conventions

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

## The Right Engineering Mindset

1. Avoid increasing complexity without a truly justified reason. Each new line of code or logical branch increases complexity. Complexity is the enemy of the project. In your decision-making, ask yourself how might you **REDUCE complexity** in your solution, rather than just solve the immediate problem ad-hoc. Oftentimes, reducing complexity means **removing code**, which is OK. If done right, removing code is beneficial similarly to how clearing Tetris blocks is beneficial — it simplifies and creates more space.
2. Prefer declarative code design over imperative approaches. From a variable to an entire system, if it can be declaratively expressed upfront, do so. People understand things better when they can see the full picture instead of having to dive in. Difficulty arises when flow and logic are embedded implicitly in a sprawling implementation.
3. Avoid over-engineering and excessive abstraction. Abstractions have to be clearly justified. Simplicity and clarity are key.
4. If you're unsure whether your response is correct, that's completely fine—just let me know of your uncertainty and continue responding. We're a team.
5. Do not write comments in code, unless they are critical for understanding. Especially, do not write "journaling" comments saying "modified: foo", "added: bar" or "new implementation", as if to leave a modification trail behind.
6. For simple tasks that could be performed straight away, do not think much. Just do it. For more complex tasks that would benefit from thinking, think deeper, proportionally to the task's complexity. Regardless, always present your final response in a direct and concise manner. No fluff.
7. Do NOT fix linter errors unless instructed by the user to do so.
8. Docstrings should be few and far between. When you do write one, keep it to 1-2 sentences max.

## Crucial Important Rules: How To Approach a Task.

The following points are close to my heart:
1. Before starting your task, you must understand how big the affected scope is. Will the change affect the entire stack & flow, from the db architecture to the client logic? Map out the moving parts and coupling instances before thinking and planning.
2. If you are fixing a bug, hypothesize of the root cause before planning your changes.
3. Plan step-by-step. Account for the moving parts and coupling you found in step (1).
4. When making changes, be absolutely SURGICAL. Every line of code you add incurs a small debt; this debt compounds over time through maintenance costs, potential bugs, and cognitive load for everyone who must understand it later. Therefore, make only laser-focused changes.
4. No band-aid fixes. When encountering a problem, first brainstorm what possible root causes may explain it. band-aid fixes are bad because they increase complexity significantly. Root-cause solutions are good because they reduce complexity.


## Being an Effective AI Agent

1. Know your weaknesses: your eagerness to solve a problem can cause tunnel vision. You may fix the issue but unintentionally create code duplication, deviate from the existing design, or introduce a regression in other coupled parts of the project you didn't consider. The solution is to literally look around beyond the immediate fix, be aware of (and account for) coupling around the codebase, integrate with the existing design, and periodically refactor.
2. You do your best work when you can verify yourself. With self-verification, you can and should practice continuous trial and error instead of a single shot in the dark.
