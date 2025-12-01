---
last_updated: 2025-12-01 14:38, 69c84d0
---
# Agents Guide

## Project overview

Newsletter aggregator that scrapes tech newsletters from multiple sources, displays them in a unified interface, and provides AI-powered TLDRs.

- Stack:
   * Python: Flask backend, serverless on Vercel
   * React 19 + Vite (frontend) (in `client/`)
   * Supabase PostgreSQL for all data persistence
   * Gemini 3 Pro Preview for TLDRs
- Storage: Project uses Supabase Database (PostgreSQL) for all data persistence (newsletters, article states, settings, scrape results). Data is stored server-side with client hooks managing async operations.
- Cache mechanism: Server-side storage with cache-first scraping behavior. Daily payloads stored as JSONB in PostgreSQL. 

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed flows & user interactions documentation and [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for a map of the project structure.

## Environment

*Note*: The `source setup.sh` command is mentioned multiple times in this document with different described effects. This is intentional: sourcing it triggers a chain of idempotent setup operations.

The single source of truth for what is available locally is the output of:

```bash
env | grep -E -o '^[A-Z_]+' | grep -e TOKEN -e API -e KEY -e SUPABASE -e VERCEL | sort -u  # Should print the names of all environment variables without values on a need-to-know basis.
```

**Run `source ./setup.sh` first thing to install all server and client dependencies and tooling, build the client, verify your environment and provide you with convenience functions and crucial context for the project.**

### Expected Environment Variables for AI Agents (Claude, Codex, Gemini, etc.)

- FIRECRAWL_API_KEY
- GEMINI_API_KEY
- GITHUB_API_TOKEN
- OPENAI_API_KEY (Optional; unused currently)
- SUPABASE_API_KEY
- SUPABASE_DATABASE_PASSWORD
- SUPABASE_SERVICE_KEY
- SUPABASE_URL
- VERCEL_PROD_DEPLOYMENT_URL
- VERCEL_PROJECT_ID
- VERCEL_TOKEN

This is true both for local and production environments.

## Development & Setup

### Running the server and logs watchdog in a background process
```bash
# Verify the environment and dependencies are set up correctly.
source ./setup.sh

# Start the server and watchdog in the background. Logs output to file.
source ./setup.sh && start_server_and_watchdog

# Verify the server is running.
source ./setup.sh && print_server_and_watchdog_pids

# Exercise the API with curl requests.
curl http://localhost:5001/api/scrape
curl http://localhost:5001/api/tldr-url
curl ...additional endpoints that may be relevant...

# Stop the server and watchdog.
source ./setup.sh && kill_server_and_watchdog
```


### Client setup

Builds client:
```bash
source setup.sh
```

### Frontend development

For frontend development with hot reload in a background process:

```bash
builtin cd client && CI=1 npm run dev
```

This runs Vite dev server on port 3000 with API proxy to localhost:5001.

#### Testing Client UI With Playwright

See [docs/testing/headless_playwright_guide.md](docs/testing/headless_playwright_guide.md) for the definitive guide on configuration, stable patterns, and environment management.

### `uv` installation and usage

- Install `uv`:
```bash
source setup.sh
```

Never run Python directly. Always use `uv` to run Python.
Do: `uv run python3 ...`. Do not: `python3 ...`.
Do: `uv run --with=dep1 python3 ...`. Do not: `pip install ...`.

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

## Practical guidance

- Trust and Verify: Lean heavily on curling and running transient Python programs in a check-verify-trial-and-error process to make sure you know what you're doing, that you are expecting the right behavior, and to verify assumptions that any particular way of doing something is indeed the right way. This is doubly true when it comes to third-party integrations, third-party libraries, network requests, APIs, the existence and values of environment variables.
- Run `source ./setup.sh` to verify the environment and dependencies are set up correctly. Use `source setup.sh && start_server_and_watchdog` and `source setup.sh && print_server_and_watchdog_pids` to confirm the local server is running. Generously exercise the API with `curl` requests (e.g., `/api/scrape`, `/api/tldr-url`) throughout the development process to catch regressions early. Use `source setup.sh && kill_server_and_watchdog` for cleanup.
- Verify every new behavior, fix or modification you make by utilizing your shell and Playwright. If possible, execute the modified flow to ensure nothing is broken.
- Make note of the various sub agents available to you (.claude/agents/) and use them in the circumstances they describe.


## Dispatching AI Sub-Agents

Delegating exploration and research tasks to sub agents leads to improved results and is context-efficient. A sub-agent dives into a specific problem area with its own fresh context window, then returns a concise summary of its findings to you. This keeps you focused on the task and keeps your main context window from ballooning. 
Deploy multiple sub-agents in parallel when your task spans multiple broad domains. A classic case: The codebase needs to be investigated across the entire call graph for any reason -> Run 3-4 parallel scouting agents, one for each of the project's subsystems. Reasons range from finding where a functionality is implemented (needle in a haystack) to gathering detailed information of multiple domains (map out the entire haystack). 

Use multiple sub-agents in parallel when a task spans several domains. For example, if you need to inspect the codebase across the full call graph, launch 3–4 scouting agents—one per subsystem. A squad of agents is optimal for handling anything from pinpointing a specific implementation (“needle in a haystack”) to mapping out wide-spanning contexts (“the entire haystack”).

### How to Run Sub-Agents
1. Either you have a built in function to run sub agents (e.g. Claude Code’s `Task`), or you don’t.
2. If you do not have such a built in function, you can install and run a sub-agent ad hoc:

```sh
# Google Gemini:
./scripts/install-gemini-cli.sh
prompt_file=$(mktemp)
echo '<tailored prompt for this agent’s subtask>' > "$prompt_file"
./scripts/run-gemini.sh "$prompt_file"
rm "$prompt_file" 
```

It is also possible to use one of the pre-made agents or commands:
```sh
# OpenAI Codex:
./scripts/install-codex-cli.sh
prompt_file=$(mktemp)
cat .claude/agents/your-agent-of-choice.md > "$prompt_file"
echo -e "\n---\n<tailored prompt for this agent’s subtask>" >> "$prompt_file"
./scripts/run-codex.sh "$prompt_file"
rm "$prompt_file" 
```

And trivially, you can parallelize agents:
```sh
./scripts/install-codex-cli.sh
COMMON_CONTEXT='<wider context to include in every agent’s prompt>'
declare -a domains=(
  'scraping subsystem'
  'web server endpoints'
  'client state management vs user interactions'
  'client rendering vs state management'
)

for domain in "${domains[@]}"; do
(
  prompt_file=$(mktemp)
  echo "$COMMON_CONTEXT" > "$prompt_file"
  echo -e "\n---\nFocus only on the ${domain}." >> "$prompt_file"
  ./scripts/run-codex.sh "$prompt_file" >> "${domain// /-}.md" 2>&1
  rm "$prompt_file"
) &
done

wait
```

Then read all new findings docs.

## Development Conventions

1. Do not abbreviate variable, function or class names. Use complete words. Write clean code.
2. Write code that fails early and clearly rather than writing fallbacks to "maybe broken" inputs. Zero "Just in case my inputs are corrupted" code. Fallback-rich code is to be avoided because it explodes complexity and often just silently propagates bugs downstream. Good code assumes that its inputs are valid and complete. It trusts upstream code to have completed its job. This ties closely to separation of concerns. And if something important fails, or an assumption is broken, fail early and clearly. Broken code should be discovered early and loudly and fixed quickly; It should not be tolerated, nor worked around.
3. Write highly cohesive, decoupled logic.
4. Early return from functions when possible.
5. Utilize existing logic when possible. Do not re-implement anything.
6. Write flat, optimized logical branches. Avoid nested, duplicate-y code. Write DRY and elegant logic.
7. Prefer `import modulename` and call `modulename.function()` rather than `from modulename import function`. Namespacing is an easy clarity win. `import os.path; os.path.join(...)` is better than `from os.path import join(...)`.
8. Always use `util.resolve_env_var` to get environment variables.
9. Add a doctest example to pure-ish functions (data in, data out).
10. `util.log` when something is going wrong, even if it is recoverable. Be consistent with existing logging style.

<Bad: fallback-rich, squirmy code>
```py
@app.route("/api/tldr-url", methods=["POST"])
def tldr_url():
    """Requires 'url' in request body"""
    # Unnecessarily defends against broken upstream guarantees.
    data = request.get_json() or {}
    url = data.get("url", "")
    result = tldr_service.tldr_url_content(url) or ""
```
</Bad: fallback-rich, squirmy code>

<Good: straightforward, upstream-trusting code>
```py
@app.route("/api/tldr-url", methods=["POST"])
def tldr_url():
    """Requires 'url' in request body"""
    # Assumes upstream guarantees are upheld (inputs are valid and complete) — thus keeps the state machine simpler.
    # If upstream guarantees are broken (e.g., missing 'url'), we WANT to fail as early as possible (in this case, `data['url']` will throw a KeyError)
    data = request.get_json()
    url = data['url']
    result = tldr_service.tldr_url_content(url)
```
</Good: straightforward, upstream-trusting code>

<Bad: unnecessarily defensive, therefore nested code>
```py
# `MyResponse.words` is an optional list, defaulting to None (`words: list | None = None`).
response: MyResponse = requests.post(...)

# Both checks are redundant:
#  1. `response.words` is guaranteed to exist by the MyResponse model
#  2. `response.words` can be coerced to an empty iterable if it is None instead of checked.
if hasattr(response, 'words') and response.words:
    for word in response.words:
        ...  # Nested indentation level
```
</Bad: unnecessarily defensive, therefore nested code>

<Good: straightforward, confident, flatter code with fewer logical branches>
```py
response: MyResponse = requests.post(...)

# The `or []` is a safe coercion to an empty iterable if `response.words` is None. In the empty case, the loop will not run, which is the desired behavior.
for word in response.words or []:
    ...  # Single indentation level; as safe if not safer than the bad, defensive example above.
```
</Good: straightforward, confident, flatter code with fewer logical branches>

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

## Documentation

1. YAML frontmatter is automatically updated in CI. Do not manually update it.
2. CLAUDE.md is a read-only exact copy of AGENTS.md. It is generated automatically in CI. It is read-only for you. Any updates should be made in AGENTS.md and not CLAUDE.md.
