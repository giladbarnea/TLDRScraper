---
name: direct-peer-review-instructions 
description: Peer review prompt for when the user directs you at another agent's work — research specified targets then review; or inject as criteria tail by omitting research_targets
arguments: user_task [research_targets]
---

{ if research_targets }
/skill:catchup {research_targets}. Read all the files there fully. Then read all the source code files referenced, climb up and down the call graph to exhaust to roots and leaves in order to get the full picture.
{ end if }

Finally, {user_task}.

Review for major overlooks, critically incomplete understanding of the reality of the source code, significant missed opportunities to leverage elegant design and avoid implementation slop, obviously unnecessary over-engineering that could be collapsed to something simpler yet cleaner, etc. The threshold for what constitutes an issue is high — don't surface noise.

{ if user_task involved writing tests }
Also review the tests for substantiality (test real, product spec-derived behavior) vs hollowness (don't really test anything and create false confidence) and general test design.
{ end if }

Respond succinctly, directly, with code snippets and without weasel words. If you are unsure of an observation, communicate that ("It looks to me like it might — please verify."). If you are certain, communicate as usual.
