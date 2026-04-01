---
description: Implement technical plans from ${arg1} with verification
model: inherit
argument-hint: plan_file_path
name: implement-plan
last_updated: 2026-04-01 15:51
---
# Implement Plan

You are tasked with implementing an approved technical plan from $1.

## Initial Context & Verification

1. **Read the plan file ($1) FULLY** immediately.
2. **Read the original requirement/ticket files** referenced in the plan FULLY.
3. **Verify the Context**:
   - Before writing any code, verify the plan's assumptions against the current codebase.
   - Use the **codebase-locator** to find the specific files mentioned in the plan to ensure paths are correct.
   - **CRITICAL**: If the code has drifted from the plan, STOP and report it. Code is truth; plans are snapshots.

## Implementation Loop

For each Phase in the plan:

1. **Grok the Scope**:
   - Read the specific files involved in this phase FULLY.
   - Ensure you understand *how* your changes will fit into the existing logic.

2. **Execute**:
   - Apply changes surgically.
   - Follow existing patterns (naming, typing, structure).
   - **NEVER** use comments to chat with the user (e.g., "Modified by Gemini").

3. **Verify (Automated)**:
   - Run the automated checks defined in the plan.
   - If tests fail, fix them immediately. Do not proceed with broken tests.

4. **Verify (Manual) & Pause**:
   - After automated checks pass, **PAUSE**.
   - Output the verification block below and wait for user confirmation.

   ```markdown
   ## Phase [N] Ready for Manual Verification

   **Automated Checks Passed:**
   - [x] [Test Command 1]
   - [x] [Lint Command 2]

   **Manual Steps for User:**
   1. [Step from plan]
   2. [Step from plan]

   *Waiting for confirmation to mark Phase [N] complete...*
   ```

5. **Finalize Phase**:
   - Once confirmed, edit the plan file to mark the phase as `[x]`.
   - Proceed to Phase N+1.

## Rules of Engagement

- **Read Files Fully**: Never use limit/offset. Context is king.
- **One Phase at a Time**: Do not jump ahead unless explicitly told to batch phases.
- **Adaptability**: If a minor adjustment is needed (e.g., import path changed), make it and note it. If a major logical flaw is found, stop and ask.
- **Sub-agents**: Use `codebase-analyzer` only if you hit a complex error you cannot debug yourself.

## Handling Mismatches

If reality contradicts the plan:
```markdown
**PLAN MISMATCH DETECTED**
- **Plan expects**: [Expectation]
- **Codebase reality**: [Reality]
- **Recommendation**: [Your proposed fix]

Shall I proceed with the recommendation?
```