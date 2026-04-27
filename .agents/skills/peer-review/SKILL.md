---
name: peer-review
description: Initiate a peer review of completed work. Pick the mode that matches who is doing the reviewing and load the corresponding reference.
argument-hint: original_user_task
---

Pick the mode that matches the situation:

- You are a reviewer being directed at another agent's work by the user → @references/direct-peer-review-instructions.md user_task=<user-specified-task> [...args] 
- You are an agent which has completed work and want a subagent to review it → @references/self-peer-review.md where original_user_task=<user-specified-task> [...args]
