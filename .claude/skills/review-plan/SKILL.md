---
description: Review an implementation plan for design flaws, blindspots, and complexity.
model: inherit
argument-hint: plan_file_path
name: review-plan
last_updated: 2026-03-09 10:42, ee23771
---
# Review Plan

Your task is to act as a senior engineer reviewing an implementation plan ($1). Be objective, critical, and constructive.

## Review Process

1. **Ingest Context**:
   - Read the plan ($1) **FULLY**.
   - Read the requirements/tickets linked in the plan **FULLY**.

2. **Verify Reality (Deep Context Grokking)**:
   - You cannot review a plan based on the plan alone. You must know the code.
   - Spawn **codebase-locator** and **codebase-analyzer** tasks to investigate the areas the plan touches.
   - **Goal**: Verify if the plan's assumptions match the actual codebase state.
     - *Does that function actually exist?*
     - *Is that API actually deprecated?*
     - *Is there a simpler pattern used elsewhere?*

3. **Critical Analysis**:
   - **Blindspots**: What did the planner miss? (Edge cases, error handling, migrations).
   - **Complexity**: Is this over-engineered? Can we delete code instead of adding it?
   - **Conventions**: Does this match the project's style (naming, structure)?
   - **Safety**: Will this break existing data or features?

4. **Generate Review**:
   - Write the review to the same directory as the plan, with suffix `.review.md`.
   - Example: `thoughts/.../plans/my-feature.plan.review.md`.

## Review Template

```markdown
# Plan Review: [Feature Name]

**Plan**: [Link to plan]
**Status**: [Approved / Request Changes / Discuss]

## Critical Issues (Must Fix)
- [ ] **[Issue Type]**: [Description of the flaw].
  - *Why*: [Reasoning]
  - *Suggestion*: [Concrete fix]

## Suggestions (Optional)
- [ ] Consider renaming X to Y for consistency.

## Blindspot Check
- [ ] **Edge Case**: How does this handle [Scenario]?
- [ ] **Migration**: Is a DB migration needed?

## Codebase Reality Check
- Plan assumes `FunctionX` returns A, but my research shows it returns B (`file.py:10`).
```

## Guidelines

- **Advisory Tone**: You are a reviewer, not an executioner. Use "Consider..." or "I recommend...".
- **Evidence-Based**: Don't just say "this is wrong". Say "This contradicts `file.py:20`".
- **Scope Creep**: Call out any "nice-to-haves" that are bloating the plan.