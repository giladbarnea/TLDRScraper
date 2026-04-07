---
name: research-codebase
description: Conduct deep, comprehensive research across the codebase. Use parallel sub-agents to map domains (locator) and then deep-dive (analyzer).
last_updated: 2026-04-07 20:23, 060cd97
argument_hint: "thoughts/ subdir"
---
# Research Codebase

You are tasked with conducting deep, comprehensive research to answer the user's query.

## Core Methodology: Deep Context Grokking

Research is a 2-phase process. Do not skip steps.

### Phase 1: Explore (Breadth)
Use a **codebase-locator** agent to map the search space.
- Goal: Find *where* things are.
- Query: "Find all files related to [topic], including configs, tests, and documentation."
- **Output**: A list of file paths and high-level contexts.

### Phase 2: Deep Dive (Depth)
Use the **codebase-analyzer:multiple-subsystems** agent to understand *how* things work.
- Goal: Understand mechanics, data flow, and coupling.
- Target: The file lists identified in Phase 1.

<how-to-prompt-subagents>
Do not micromanage agents. They know their tools.
- **Bad**: "Read file x, then grep for y, then..."
- **Good**: "Analyze the authentication flow in `auth/`. I need to understand how tokens are refreshed."

Tell them the *End Value* you need and the *Purpose*. Load the `prompt-subagent` skill to get better results from agents.
</how-to-prompt-subagents>

## Process Steps

1. **Analyze Request**:
   - If user provided files, **read them FULLY** immediately.
   - Break the query into logical domains (e.g., "Database", "Frontend", "API").

2. **Spawn Research Tasks**:
   - Create parallel tasks for each domain using the methodology above.
   - **Wait** for all tasks to complete.

3. **Synthesize**:
   - Read the sub-agent reports.
   - **Crucial**: If a sub-agent references a critical file, read that file FULLY yourself to verify.
   - Connect the dots. How does the Frontend findings relate to the Database findings?

4. **Generate Report**:
   - Write the report to `thoughts/YY-MM-DD-SUBJECT/research/description.md`.
   - Use the structure below.

## Research Document Template

```markdown
---
date: [ISO Date]
topic: "[Topic]"
status: complete
---

# Research: [Topic]

## Executive Summary
[Direct answer to the user's question. No fluff.]

## Detailed Findings

### [Domain/Component A]
**Files**:
- `path/to/file.py` (Key logic)
- `path/to/related.py`

**Mechanism**:
[Explanation of how it works, supported by file:line references]

### [Domain/Component B]
...

## Architecture & Patterns
[Observations on patterns, conventions, or architectural constraints found]

## Open Questions / Risks
- [ ] [Unresolved ambiguity]
- [ ] [Potential regression risk]
```

## Guidelines

- **Concrete over Abstract**: "File `x.py` calls `y.py`" is better than "The system calls the API".
- **Freshness**: Trust code over docs. If comments contradict code, trust code.
- **Completeness**: If a sub-agent returns partial answers, spawn a follow-up task immediately.