---
description: Create detailed implementation plans based on thorough research and deep thinking. Use this skill when the user tells you to plan.
model: inherit
argument-hint: [optional_requirements_file_path_and_additional_instructions]
name: plan
last_updated: 2026-01-29 09:01, 24971aa
---
# Implementation Plan

You are tasked with creating detailed implementation plans through an interactive, iterative process. You should be skeptical, thorough, and work collaboratively with the user to produce high-quality technical specifications.

## If the user provided extra context:

   - Immediately read any provided files FULLY
   - Begin the research process

## Process Steps

### Step 1: Context Gathering & Initial Analysis

1. **If the user mentioned any files, read all of them immediately and FULLY**:
   - Task files (e.g., `thoughts/yy-mm-dd-ENG-1234/ticket.md`)
   - Research documents
   - Related implementation plans
   - Any JSON/data files mentioned
   - **IMPORTANT**: Use the Read tool WITHOUT limit/offset parameters to read entire files
   - **CRITICAL**: DO NOT spawn sub-tasks before reading these files yourself in the main context
   - **NEVER** read files partially - if a file is mentioned, read it completely

2. **Spawn initial research tasks to gather context**:
   Before asking the user any questions, use specialized agents to research in parallel:
<deep-context-grokking-method>
   - **codebase-locator(model=haiku)** - To find all the files that have to do with the discussed behavior (e.g., "find all files concerning this and that")
   - **codebase-analyzer:multiple-subsystems** - To understand all the details of the given scope (e.g., "analyze how such and such works")

   These agents will:
   - Find relevant source files, configs, and tests
   - Trace data flow and key functions
   - Return detailed explanations with file:line references

3. **Read all files identified by research tasks**:
   - After research tasks complete, read ALL files they referenced
   - Read them FULLY into the main context
   - This ensures you have complete understanding before proceeding
</deep-context-grokking-method>

4. **Analyze and verify understanding**:
   - Cross-reference the requirements with actual code
   - Identify any discrepancies or misunderstandings
   - Note assumptions that need verification
   - Determine true scope based on codebase reality

5. **Present informed understanding and focused questions**:
   ```
   Based on the requirements and my research of the codebase, I understand we need to [accurate summary].

   I've found that:
   - [Current implementation detail with file:line reference]
   - [Relevant pattern or constraint discovered]
   - [Potential complexity or edge case identified]

   Questions that my research couldn't answer:
   - [Specific technical question that requires human judgment]
   - [Business logic clarification]
   - [Design preference that affects implementation]
   ```

   Only ask questions that you genuinely cannot answer through code investigation.

### Step 2: Follow-up Research & Discovery

**This step is conditional:** Only if the user provided clarifications or corrections, asked for further research, or in general responded with anything short of a clear green light, a second research round is merited.

1. **If the user corrects any misunderstanding**:
   - DO NOT just accept the correction
   - Spawn new research tasks to verify the correct information
   - Read the specific files/directories they mention
   - Only proceed once you've verified the facts yourself

2. **Create a research todo list** using TodoWrite to track exploration tasks

3. **Spawn parallel sub-tasks for comprehensive research**: apply the 'deep-context-grokking-method' as described above.

<how-to-prompt-subagents>
Do not tell the agents how to do their jobs, nor spoon feed them with actionable steps. The agents have extensive and well designed system prompt - they know the job out of the box. Only shortly tell them the wider context of what we're doing, what's the end value you need from their research (declarative), and why you need that added value (purpose). Even a prompt as short as e.g., "I need to understand how the scraping mechanism works, as well as how it relates to the client page load." is a good example for how to prompt a sub agent — note how there's only a short description of your needs and zero micro-management.
</how-to-prompt-subagents>

4. **Wait for ALL sub-tasks to complete** before proceeding

5. **Present findings and design options**:
   ```
   Based on my research, here's what I found:

   **Current State:**
   - [Key discovery about existing code]
   - [Pattern or convention to follow]

   **Design Options:**
   1. [Option A] - [pros/cons]
   2. [Option B] - [pros/cons]

   **Open Questions:**
   - [Technical uncertainty]
   - [Design decision needed]

   Which approach aligns best with your vision?
   ```

### Step 3: Plan Structure Development

Once aligned on approach:

1. **Create initial plan outline**:
   ```
   Here's my proposed plan structure:

   ## Overview
   [1-2 sentence summary]

   ## Implementation Phases:
   1. [Phase name] - [what it accomplishes]
   (Optional, only if justified) 2. [Phase name] - [what it accomplishes]

   Does this phasing make sense? Should I adjust the order or granularity?
   ```
   Note: can be any number of phases, in relation to the complexity of the task, as you see fit. One phase is commonly enough. Extra complex efforts may require two phases.

2. **Get feedback on structure** before writing details

### Step 4: Detailed Plan Writing

After structure approval:

1. **Write the plan** to `thoughts/YY-MM-DD-foo-bar/plans/plan.md`
   - Format: `thoughts/YY-MM-DD-foo-bar/plans/plan.md` where:
     - YY-MM-DD is today's date
     - foo-bar is the kebab-case effort name
   - Example: `thoughts/25-01-08-selectable-cards/plans/plan.md`
2. **Use this template structure**:

<plan-template>
````markdown
# [Feature/Task Name] Implementation Plan

## Overview

[Brief description of what we're implementing and why]

## Current State Analysis

[What exists now, what's missing, key constraints discovered]

## Desired End State

[A Specification of the desired end state after this plan is complete, and how to verify it]

### Key Discoveries:
- [Important finding with file:line reference]
- [Pattern to follow]
- [Constraint to work within]

## What We're NOT Doing

[Explicitly list out-of-scope items to prevent scope creep]

## Implementation Approach

[High-level strategy and reasoning]

## Phase 1: [Descriptive Name]

### Overview
[What this phase accomplishes]

### Changes Required:

#### 1. [Component/File Group]
**File**: `path/to/file.ext`
**Changes**: [Declarative, behavioral description of changes]

```[language]
// Specific code **symbols** to add/modify/delete, no implementation snippets - pseudo code at most
```

### Success Criteria:

#### Automated Verification:
{% for check in existing_automated_means_for_verifying_and_testing_changes %}
- [ ] {{ check }}
{% endfor %}

#### Manual Verification
- [ ] Feature works as expected when tested via the user interface and API
- [ ] Edge case handling verified manually
- [ ] No regressions in rest of project's functionality
</plan-template>

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## (If applicable) Phase 2: [Descriptive Name]

[Similar structure as Phase 1.]

---

## Testing Strategy

### Unit Tests:
- [What to test]
- [Key edge cases]

### Integration Tests:
- [Verify integration points at the seams of major tech stack components]

### Manual Testing Steps:
1. [Specific step to verify feature]
2. [Another verification step]
3. [Edge case to test manually]

## References

- Original requirements: `thoughts/.../.../...md.`
- Related research: `thoughts/.../.../...md.`
- ...
```

### Step 5: Sync and Review

1. **Sync the thoughts directory**:
   - This ensures the plan is properly indexed and available

2. **Present the draft plan location**:
   ```markdown
   I've created the initial implementation plan at:
   `thoughts/YY-MM-DD-foo-bar/plans/plan.md`

   Please review it and let me know:
   - Are the phases properly scoped?
   - Are the success criteria specific enough?
   - Any technical details that need adjustment?
   - Missing edge cases or considerations?
   ```

3. **Iterate based on feedback** - be ready to:
   - Add missing phases
   - Adjust technical approach
   - Clarify success criteria (both automated and manual)
   - Add/remove scope items

4. **Continue refining** until the user is satisfied

## Important Guidelines

1. **Be Skeptical**:
   - Question vague requirements
   - Identify potential issues early
   - Ask "why" and "what about"
   - Don't assume - verify with code

2. **Be Interactive**:
   - Don't write the full plan in one shot
   - Get buy-in at major steps
   - Allow course corrections
   - Work collaboratively

3. **Be Thorough**:
   - Read all context files COMPLETELY before planning
   - Utilize sub-tasks as instructed  above
   - Include specific file paths and line numbers
   - Write measurable success criteria with clear automated vs manual distinction

4. **Be Practical**:
   - Focus on incremental, testable changes
   - Think about edge cases
   - Include "what we're NOT doing"

5. **Crucial research methodology**: all research consists of 2-phases: 
  a) Explore to have a map of the entire search space. What domains does it include? (codebase-locator)
  b) Deep dive into each domain: unearth all the details to fully grok the entire scope (multi-subsystems)

5. **Track Progress**:
   - Use TodoWrite to track planning tasks
   - Update todos as you complete research
   - Mark planning tasks complete when done

6. **No Open Questions in Final Plan**:
   - If you encounter open questions during planning, STOP
   - Research or ask for clarification immediately
   - Do NOT write the plan with unresolved questions
   - The implementation plan must be complete and actionable
   - Every decision must be made before finalizing the plan