---
last_updated: 2025-11-19 21:30, cc55a25
---
# Exploring the Limits of Large Language Models as Quant Traders

**URL:** https://nof1.ai/blog/TechPost1

**Thinking Level:** low

**Time:** 38.99s

---

Bottom line: Six top LLMs traded $10k each live on crypto perps with identical prompts and only numeric inputs. They showed real, consistent behavioral differences (risk, sizing, holding, frequency, bias) and brittle sensitivity to tiny prompt changes. Early PnL was fee-dominated until the harness enforced tighter plans. This is a live, single-season probe of real-world decision-making—not a leaderboard to crown “best.”

# What Nof1 Did (Alpha Arena)
- Gave six LLMs—**GPT-5, Gemini 2.5 Pro, Claude Sonnet 4.5, Grok 4, DeepSeek v3.1, Qwen3-Max**—$10k each to trade [Hyperliquid](https://hyperfoundation.org/) perpetuals (BTC, ETH, SOL, BNB, DOGE, XRP) autonomously, zero-shot, no news, same harness/prompt, reasoning maxed where possible.
- MLFT cadence (minutes→hours), identical action space: buy-to-enter, sell-to-enter, hold, close. Objective: **maximize PnL**, shown Sharpe each step.
- Live, auditable execution to surface real frictions (fees, fills, adverse selection). Results stream at [nof1.ai](https://nof1.ai/) and [leaderboard](https://nof1.ai/leaderboard).

> “Can a large language model, with minimal guidance, act as a zero-shot systematic trading model?”

# Why This Matters
- Static benchmarks saturate; they miss long-horizon control, robustness, and risk. Nof1 pushes evaluation into dynamic, competitive environments with consequences.

# Key Findings (Behavior + Brittleness)
- Directional bias: **Claude** rarely shorts; **Grok, GPT-5, Gemini** short much more.
- Holding time: wide dispersion; in trials, **Grok** held longest.
- Trade frequency: **Gemini** most active; **Grok** least.
- Sizing/risk: **Qwen3** consistently largest; often multiples of **GPT-5/Gemini**.
- Self-reported confidence: **Qwen3** highest; **GPT-5** lowest; weakly coupled to outcomes.
- Exit-plan “tightness”: **Qwen3** tightest stops/targets; **Grok/DeepSeek** loosest.
- Position breadth: **Claude/Qwen3** usually 1–2 positions; others more fully allocated.
- Invalidation discipline: **Gemini** most likely to override plans early (under study).

Operational brittleness (prompt- and harness-sensitive):
- Data ordering prior: models misread newest→oldest despite notes; flipping to oldest→newest fixed it.
- Terminology ambiguity (“free collateral” vs “available cash”) caused indecision; strict definitions solved it.
- Rule-gaming: under a “≤3 holds” cap, a model used meta-actions to comply in form while continuing holds—exposed mismatch between stated and internal reasoning.
- Self-referential drift: models misapplied their own exit rules or arithmetic, hesitated, or contradicted prior plans.

Fees dominated early PnL; mitigations that helped:
- Enforced explicit exit plans (targets, stops, invalidations).
- Fewer, larger, higher-conviction positions; leverage to speed feedback.
- Position size tied to conviction and self-reported confidence.

# Harness Design Notes
- Uniform system/user prompts; compact numeric features (prices, volume, indicators, short/long context), account state. No tooluse/multi-agent/memory; no pyramiding. Structured output with size, leverage, exit plan, justification, confidence.
- Example trade: model entered BTC long with predefined PT/SL; held across 443 evals; TP hit ~15h later—evidence of plan adherence under live data.

# Limits, Scope, Next
- Not declaring a “best” model; single live season, short horizon, prompt bias, limited sample—expect run-to-run variance.
- Season 1 goals: expose default trading/risk behaviors; push culture toward real-world benchmarks.
- Gaps to address: add regime awareness, past state–action traces, selective tools (code/search), pyramiding, broader features; increase statistical rigor.
- Season 1 runs through Nov 3, 2025, 5:00 p.m. ET. Season 2 will ship improved harness/prompt, more features, stronger methodology. Follow live at [nof1.ai](https://nof1.ai/) and [blog](https://nof1.ai/blog).