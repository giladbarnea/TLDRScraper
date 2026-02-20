---
last_updated: 2026-02-20 07:52
---
# Article Digest Feature — Planning Task

## Rough Feature Definition
I want to brainstorm about a new feature - generating a digest of selected articles based on their contents, using Gemini 3.
This feature spans the entire stack: starts at the client (article selection UI, triggering digest generation), goes through the backend (new API endpoint, Gemini integration for multi-article digest), persists to Supabase (storing digest results), then back to the client (displaying the digest in a ZenOverlay).

## Your Task
Read `.claude/skills/catchup/SKILL.md` and follow its instructions to gather project context. Then read all files in `thoughts/26-02-20-article-digest/` to absorb the domain research that's already been done.

Then write a plan to `thoughts/26-02-20-article-digest/plan.codex.md`.

Use an **advisory style** — hypothesize rather than assert. Leave room for discussion. Write as if you're proposing to a collaborator, not dictating.

### Plan in Two Passes

**Pass 1 — High-Level Architecture:**
- What are the inputs and outputs of the digest feature end-to-end?
- What is the data flow from user action to rendered digest?
- Where does the digest live in the existing architecture? What existing systems does it touch?

**Pass 2 — Module-Level Enrichment:**
- For each module/layer the feature touches, get specific about what changes.
- Identify which existing patterns to follow (e.g., useSummary → useDigest, summarizer.py → digest prompt).
- Identify where the feature diverges from existing patterns and why.
- Be specific about data shapes, storage keys, and API contracts — but stay at the interface level, not implementation details. No function names, no concrete code.

### Finish With
A short mention of any upstream or downstream systems or flows that by gut feeling could be broken by the planned changes, and therefore should be watched out for during implementation.

### Style Constraints
- No implementation details, no function names, no concrete code.
- Advisory style: "could", "might consider", "one approach would be".
- Focus on architecture, data flow, and interfaces.
