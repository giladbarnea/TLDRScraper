---
name: architecture-sync-current-changes
description: Sync ARCHITECTURE.md with current changes
last_updated: 2025-12-01 19:51, 4d0cb1d
---
`ARCHITECTURE.md` was a very good representation of the project before your changes. Given your changes, `ARCHITECTURE.md` is now outdated in some aspects. Your task is to make it as good a representation of the project in its current state. 

For context, to understand what ARCHITECTURE.md is trying to achieve:
<original-architecture-md-creation-prompt>
## Purpose
The purpose of the task at large is two-fold:
1. map out precisely the call graphs of each feature the project provides, end to end
2. build a crisp state machine of the flow of each feature.

## Strategy
I want you to implement the task in a layered approach. like an oil painter, the drawing is an analogy for the task and the canvas is the codebase. Accordingly, make multiple passes over the codebase to cultivate a deep understanding of it:

-   Start with rough shapes and composition across the whole canvas
-   Gradually add detail in passes
-   Refine everything together rather than finishing one section completely before moving to the next
-   blocking in broad areas first, then building up layers of detail across the entire work.
	

The end result should be a sharp and precise ARCHITECTURE.md with a clear specification of available user interactions → state transitions (`#purpose-1`), and user interactions → call graphs (`#purpose-2`). 

## Task
Roughly, here are the passes you should perform:
1. Investigate the major features and user interactions in the project that are directly related to or affected by your recent change.
2. Succinctly enumerate the various state transitions associated with it, if any.
3. List the big ticket code components involved with the feature, by call order, from client to backend. Associate components with major state transitions.
4. Step by step, like a compiler recording the state machine, list out the call graph exactly. Keep track of the passed values and thereby the state from step to step.
</original-architecture-md-creation-prompt>

---

<real-task-from-user>
## Real Task
read ARCHITECTURE.md in full. Given your changes, does ARCHITECTURE.md now have any hard false positives or false negatives? by false positives i mean details that are unequivocally false — misinformation; by false negatives i mean omitting crucial details. i am not interested in “soft” issues like style or emphasizing any particular aspect in the doc (e.g. not interested in matters of degree), but only in real informational bugs.

## How to perform the real task

Make sure you have a solid grip of the changes you made.

<read-this-only-if-changes-are-wide otherwise="skip">
Make sure you have a solid grip of the changes you made. Leverage the `codebase-locator` agent to perform pass #1 ("Investigate the major features..."). Then, delegate passes #2-to-#4 to `codebase-analyzer-narrow` agent with the files `codebase-locator` has come up with. `codebase-analyzer-narrow`'s final answer will provide you with all the information you need to perform the real task (`## Real Task` section above dealing with detecting and fixing false positives and false negatives).
</read-this-only-if-changes-are-wide>

If and only if there are any hard false positives or false negatives, update ARCHITECTURE.md accordingly. Be very surgical; update only what's needed, where do not emphasize your changes. Your only goal is to make ARCHITECTURE.md accurate again.
</real-task-from-user>
