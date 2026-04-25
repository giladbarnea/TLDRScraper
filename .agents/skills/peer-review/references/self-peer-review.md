---
name: self-peer-review
description: Dispatch a subagent to review your own committed work
arguments: original_user_task 
---

First, commit your work to have a commit reference. Then dispatch a large, high-thinking subagent with the following prompt:

---

The user has given me this task:
<original-user-task>
{original_user_task}
</original-user-task>

I have attempted to complete it. It's committed to {commit_sha}.

Conduct thorough documentation and source code research. Alternate between `git show` and `gsd`/`git diff` to see the before and after of my work. Follow call/dependency graphs completely to roots and leaves.

{ if original_user_task references skills }
Load the referenced skills yourself for complete understanding: { skill_names }
{ end if }

@references/peer-review-directly-from-user.md task="review my work" tests={ true if work included tests }
