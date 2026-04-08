---
name: co-develop
description: Parallel development with another LLM in the background
argument-hint: co-model-name co-model-results-file-path
context: fork
last_updated: 2026-04-08 14:36, 0a16acd
---
Before you start, prompt `scripts/run-agent.sh -m <MODEL> <PROMPT> 2&1 | tee /tmp/log.md` where model is $1 and prompt is exactly the prompt I have given you verbatim.
I have probably asked you to persist your own results to a file. Avoid a race condition and tell the agent to write to a slightly different file name $2. And add one phrase to my original prompt: "You're running non-interactively. Don't stop for user interaction."

Run it in a background shell with a 15 minutes timeout. Then forget about it and proceed with your task.
If if you've completed your task before the agent, await in 120 seconds intervals for a total of 10 more minutes max.

Then read the file the agent has output and consider whether there's anything to take/cherry pick from it.
To adopt any notion, it has to answer all of the following criteria:
1. It doesn't increase the overall design complexity (non-negotiable). Conversely, it gains points if it reduces complexity.
2. It's either better from your alternative, or it increases the cohesiveness/elegance of the overall design.

We can talk about it and make the decision together.