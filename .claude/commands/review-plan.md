---
description: Review an implementation plan for design flaws and blindspots
model: inherit
argument-hint: plan_file_path
name: review-plan
---
# Plan Review Task

Your task is to critically review an implementation plan.

## Instructions

1. **Read and Understand the Plan**
   - Read `${1}` thoroughly
   - Understand the problem being solved and the proposed solution

2. **Identify Knowledge Gaps**
   - Think about what context you're lacking to assess this plan properly
   - What do you need to know about the codebase architecture?
   - What flows, components, or patterns are relevant?

3. **Research the Codebase**
   - Study all aspects of the codebase relevant to this plan
   - Focus on:
     - Cache mechanism and storage flow
     - Scraping logic and date handling
     - Client-server interaction patterns
     - Edge cases in date/time handling
   - Read relevant code files, understand the call graph
   - Review ARCHITECTURE.md and other docs as needed

4. **Re-evaluate with Context**
   - Go back to the plan with your renewed understanding
   - Read it critically with full context

5. **Critical Review**
   - Does the plan have any hard blindspots?
   - Are there major design flaws?
   - Could the intended outcome be achieved with a markedly better, different approach?
   - Does it align with the project's architecture and conventions?
   - Does it handle edge cases properly?
   - Is it unnecessarily complex or could it be simpler?

6. **Write Review**
   - The answer could just as plausibly be "no" (plan is good) as "yes" (plan has issues)
   - Be honest and thorough
   - If you find issues, suggest concrete alternatives
   - If the plan is solid, explain why
   - Write your conclusion to: `${1%.md}.review.md` (same directory as the plan, with .review.md suffix)

## Output Format

Your review should include:
- Summary of what the plan proposes
- Key codebase patterns/flows you researched
- Assessment of the plan's approach
- Any blindspots, flaws, or better alternatives identified
- Final recommendation (approve as-is / approve with modifications / reject with alternative)
