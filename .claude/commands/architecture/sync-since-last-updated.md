---
name: architecture-sync-since-last-updated
description: "Sync ARCHITECTURE.md with changes since it was last updated"
last_updated: 2025-12-10 07:26, b46af66
---
`ARCHITECTURE.md` was written at some point in time. It was a very good representation of the project at that time. Since then, the project has evolved, therefore `ARCHITECTURE.md` is outdated in some aspects. Your task is to make it as good a representation of the project in it's current state. For context:

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
1. Investigate the major features and the interactions the user can have with the project, grouped by feature. 
2. For each feature, succinctly enumerate the various state transitions associated with it, if any.
3. For each feature, List the big ticket code components involved with the feature, by call order, from client to backend. Associate components with major state transitions.
4. For each feature, step by step, like a compiler recording the state machine, list out the call graph exactly. Keep track of the passed values and thereby the state from step to step.
</original-architecture-md-creation-prompt>

<real-task-from-user>

## Real Task

Read ARCHITECTURE.md in full. Use its `last_updated` frontmatter field as an anchor in time to understand what has changed in the codebase’s architecture since. Given your sharp understanding of the codebase’s changes, does ARCHITECTURE.md now contain any hard false positives or false negatives? By false positives, I mean information that is unequivocally wrong — misinformation. By false negatives, I mean omitting crucial information. The keyword is “crucial”: I am not interested in “soft” issues like style or how strongly something is emphasized (I’m not interested in matters of degree), but only in real informational errors — information whose absence would leave ARCHITECTURE.md fundamentally incomplete.

## How to perform the real task

Make sure you have a solid grip of the changes that have been made.

Leverage the `codebase-locator` to perform pass #1 ("Investigate the major features..."). Then, delegate passes #2-to-#4 to `codebase-analyzer:single-subsystem` agent with the files `codebase-locator` has come up with. `codebase-analyzer:single-subsystem`'s final answer will provide you with all the information you need to perform the real task (`## Real Task` section above dealing with detecting and fixing false positives and false negatives).

If and only if there are any hard false positives or false negatives, update ARCHITECTURE.md accordingly. Be very surgical; update only what's required. Do not emphasize your changes.  Any update needs to take up no more space than its significance proportional to the entire project's architecture. Your only goal is to make ARCHITECTURE.md truthful again.
</real-task-from-user>
