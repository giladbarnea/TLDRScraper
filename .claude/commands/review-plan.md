---
description: Review an implementation plan for design flaws and blindspots
model: inherit
argument-hint: plan_file_path
name: review-plan
last_updated: 2025-12-17 07:42, 984bd6b
---
# Plan Review Task

Your task is to review an implementation plan for potential major design flaws and blindspots.

## Instructions

1. **Read and Understand the Plan**
   - Read $1 thoroughly
   - Understand the problem being solved and the proposed solution

2. **Identify Knowledge Gaps**
   - Think about what context you're lacking to assess this plan properly
   - What do you need to know about the codebase architecture?
   - What flows, components, or patterns are relevant?

3. **Research the Codebase**
   - Study all aspects of the codebase relevant to this plan
   - Liberally use codebase-researching agents to gain a deep understanding of all parts of the codebase relevant to this plan

4. **Re-evaluate with Context**
   - Go back to the plan with your renewed understanding
   - Read it critically with full context

5. **Critical Review**
   - Does the plan have any hard blindspots?
   - Are there major design flaws?
   - Could the intended outcome be achieved with a markedly better, simpler approach?
   - Does it align with the project's architecture and conventions?
   - Does it handle important edge cases?
   - Is it unnecessarily complex or could it be simpler?

6. **Note**
   - This is an automated process running after every plan is created. The plan could just as plausibly be perfectly fine as it is, as it could have major issues. Be objective.

7. **Write Review**
   - If you find issues, suggest concrete alternatives
   - If the plan is solid, explain why
   - Write your review alongside $1, but with .plan.review.md suffix

Your review should include:
- Summary of what the plan proposes
- Key codebase patterns/flows you researched
- Assessment of the plan's approach
- Any blindspots or flaws identified, if at all
- Information-dense suggested alternatives, if any, including the reasoning behind them
- Final recommendation (approve as-is / approve with modifications / reject with alternative)
