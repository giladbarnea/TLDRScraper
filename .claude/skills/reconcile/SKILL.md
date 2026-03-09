---
name: reconcile
description: Judge between a plan and its review to reach a finalized conclusion
model: inherit
argument-hint: [directory_containing_plan_and_review]
last_updated: 2026-03-09 10:42, ee23771
---
A plan and a review of that plan have both been devised and written to $1. You are tasked with judging which case is more valid — the plan or its criticiser — and reaching a finalized conclusion. Whatever your verdict is, it will be accepted and acted upon.

1. **Read and Understand the Plan and its Reivew**
   - Study the two docs
   - Understand the problem being solved, the proposed solutions and the counter arguments of the review

2. **Identify Knowledge Gaps**
   2.1) Think about what context you're lacking to assess the plan and its review properly
   2.2) What do you need to know about the codebase and the project?
   2.3) What flows, components, or contexts are relevant?
   2.4) What systems and files may be affected by the proposed changes?
   2.5) Read **everything** that can help with 2.1-2.4
   2.6) If you haven't already, start by reading AGENTS.md, ARCHITECTURE.md, PROJECT_STRUCTURE.md. Then proceed to study the codebase.

3. **Research the Codebase**
   - Study all aspects of the codebase relevant to this plan
   - Liberally use codebase-researching agents to gain a deep understanding of all parts of the codebase relevant to this plan. If sub-agents are unavailable, read files generously and fully.

4. **Re-evaluate with Context**
   - Go back to the plan and its review with your renewed understanding
   - Read them critically with full context

5. Consider the quality of the cases and arguments, then conclude which approach should be taken by implementers. Weigh your judgment by the truthfulness of the assumptions and conclusions made by each party. Write your verdict to a file alongside the markdown files you’ve read.