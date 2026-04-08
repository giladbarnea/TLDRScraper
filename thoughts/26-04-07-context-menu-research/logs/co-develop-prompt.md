---
last_updated: 2026-04-08 15:17
---
Catchup and invoke the plan skill (total autonomy) on thoughts/26-04-07-context-menu-research/**/*. Write your results to a thoughts/.../plan-x.md.

/co-develop gemini-3.1-pro plan-g.md

PS: scripts/run-agent.sh is relatively new. I'm no sure it 100% works. Sometimes when invoked it says that it doesn't recognize the model name and falls back to something else. I need gemini-3.1-pro-preview. Before anything else, smoke test by running `scripts/run-agent.sh -m gemini-3.1-pro "who are you?" 2>&1` and checking whether it says gemini and not something generic. If it doesn't work, try `scripts/run-agent.sh -m openrouter/google/gemini-3.1-pro-preview "who are you?" 2>&1`.

If you can't get gemini, don't do the task. Stop.

You're running non-interactively. Don't stop for user interaction. Write your final result to thoughts/26-04-07-context-menu-research/plans/plan-g.md.
