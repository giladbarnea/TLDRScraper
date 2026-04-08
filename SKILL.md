---
name: prompt-subagent
description: Instructions for _how_ to prompt a subagent to perform any task. Load this skill before dispatching a subagent.
---

1. Orient the agent to the project: tell it to read key context files (`README.md`, `CLAUDE.md`/`AGENTS.md`, `ARCHITECTURE.md`) and any relevant domain context directories—enough for it to understand *what this project is for* before starting the task.
2. Be generous in giving the agent wider context—understanding *why* it's performing the task will boost its performance. Don't micromanage nor over-instruct it. The agent already has a highly detailed system prompt. It is highly intelligent, just like you, and is able to navigate through uncertainties well without external guidance. Avoid prescribing instructions or giving it "how-to" examples; Avoid prescribing it which files/symbols/paths to look at; just declare what kind of *understanding* you're seeking.
   Sharing only why it's been dispatched, and what you hope to achieve by the time the agent completes its task directly frees it up to find the best way to achieve *your* goal without being biased and limited by your own knowledge and assumptions.
3. Remind it that it too can spawn subagents to perform tasks, utilize skills, etc.
