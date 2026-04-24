---
name: peer-review
description: Prompt a subagent to review your work. Only use the skill when the user says so
---
First, commit your work to git to have a commit reference at hand.
Then dispatch a large, high-thinking subagent to review your work. 
Like the academic peer review method, to guarantee objectivity, you must hand the subagent only the original task I have given you verbatim, a request for review as outlined below, and nothing more. 
Not interpretations, no decision rationals, no "why", no "specifically, look at ...". These all constitute biasing the subagent. 

Use this template exactly:

<prompt-template>

The user has given me this task:
<original-user-task>
{{ ... }}
</original-user-task>

I have attempted to complete it. It's committed to {{ commit sha }}.
Conduct a thorough documentation and source code research and deep thinking, then alternate between git show and `gsd`/git diff to see the before and after of my work. Optimize recall in this research phase, and follow call/dependency graphs completely to roots and leaves.
{ % if user original task includes references to skills % }
  Load the referenced skills yourself for complete understanding: {{ skill names }}
{ % end if % }
Review my work for major overlooks, crtically incomplete understanding of the requirements, significant missed opportunities to leverage elegant design and avoid implementation slop, etc.
{ % if my original user task instructed to write tests % }
  Also review the tests for substantiality (test real, product spec-derived behavior) vs hollowness (don't really test anything and create false confidence) and general test design.
{ % end if % }
Respond succinctly, directly, with code snippets and without weasle words. If you are unsure of an observation, communicate that ("It looks to me like it might - please verify."). If you _are_ certain, communicate as usual.

</prompt-template>
