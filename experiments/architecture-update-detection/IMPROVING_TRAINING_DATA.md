---
last_updated: 2025-11-27 08:28, dd5b623
---
# Improving Training Data: The Lookahead Problem

## Overview

The architecture update detection dataset has a fundamental challenge: **temporal labeling ambiguity**. When analyzing historical commits, we need to distinguish between:

1. Commits that didn't update architecture
2. Commits that may have needed an architecture update but didn't (potentially corrected in later commits)

This document describes the "lookahead" technique for identifying case #2 and improving training data quality.

## The Lookahead Technique

**Concept:** Look forward in git history to detect when a commit's missing architecture update was corrected in a subsequent commit.

**Pattern:**
```
Commit N:   [Code changes to components/hooks] → architecture_updated: false
Commit N+1: [Other changes]
Commit N+2: [ARCHITECTURE.md body updated] → Likely documenting changes from N
```

**Inference:** If commit N changed user-facing behavior (components, hooks, flows) and commit N+1 or N+2 updated ARCHITECTURE.md, then commit N likely should have updated it.

## Current Implementation

The `detect_retrospective_labels()` function in `generate_architecture_dataset.py` implements basic lookahead:

```python
# For each commit N:
for j in range(i + 1, min(i + 4, len(commits))):  # Look ahead 1-3 commits
    later_commit = commits[j]

    if later_commit['architecture_body_changed']:
        has_meaningful_changes = (
            commit['jsx_components'] > 0 or
            commit['js_hooks'] > 0 or
            commit['msg_behavior_change'] or
            commit['msg_component_change']
        )

        if has_meaningful_changes:
            commit['should_have_updated'] = True
            break
```

**Strengths:**
- Simple, deterministic
- Successfully detected commit `98fb9711` (changed 2 components, updated 1 commit later)

**Weaknesses:**
- Fixed lookahead window (3 commits) may be too short or too long
- No semantic understanding of whether later doc changes relate to earlier code changes
- Produces false positives (e.g., commit `827e1833` with 0 components)

## Improving Lookahead: Ideas for Refinement

### 1. Semantic Similarity Between Commits

**Problem:** Current approach assumes any architecture update within 3 commits relates to the current commit.

**Improvement:** Check if the later architecture update is semantically related to the earlier code changes.

Heuristics:
- Compare file paths: Did commit N change `FoldableContainer.jsx` and commit N+2's architecture diff mention "foldable" or "container"?
- Compare commit messages: Does commit N+2's message reference the same feature/component?
- Check for issue/PR references: Do both commits reference the same PR or issue number?

Example:
```python
def commits_are_related(commit_n, commit_n_plus_k):
    """Check if architecture update in N+K likely documents changes from N."""

    # Extract component names from commit N
    components = [f.split('/')[-1].replace('.jsx', '')
                  for f in commit_n['files']
                  if f.endswith('.jsx')]

    # Get architecture diff from N+K
    arch_diff = get_architecture_diff(commit_n_plus_k['commit_hash'])

    # Check if any component names appear in the architecture diff
    for component in components:
        if component.lower() in arch_diff.lower():
            return True

    # Check for PR/issue number overlap
    pr_n = extract_pr_number(commit_n['message'])
    pr_nk = extract_pr_number(commit_n_plus_k['message'])
    if pr_n and pr_n == pr_nk:
        return True

    return False
```

### 2. Adaptive Lookahead Window

**Problem:** Fixed 3-commit window may miss delayed documentation or flag unrelated updates.

**Improvement:** Vary lookahead distance based on commit characteristics.

Heuristics:
- Larger changes (more components) → look further ahead (up to 5 commits)
- Smaller changes (1-2 components) → shorter window (1-2 commits)
- Stop lookahead at major feature boundaries (different PR branches)

### 3. Manual Curation of Edge Cases

**Problem:** Automated lookahead will always produce some incorrect labels.

**Improvement:** Flag uncertain cases for manual review.

Process:
1. Run automated lookahead
2. For each retrospective label, compute confidence score
3. Export low-confidence cases to CSV for manual review
4. Human reviews and corrects labels
5. Use corrected labels for training

Confidence scoring:
```python
def compute_confidence(commit, later_commit, commits_between):
    """Score from 0 (uncertain) to 1 (confident)."""
    score = 0.5  # Baseline

    # Boost confidence if:
    if commits_are_related(commit, later_commit):
        score += 0.3
    if commits_between <= 2:
        score += 0.1
    if commit['jsx_components'] >= 2:
        score += 0.1

    # Reduce confidence if:
    if commit['jsx_components'] == 0 and commit['js_hooks'] == 0:
        score -= 0.4
    if commits_between > 3:
        score -= 0.2

    return min(max(score, 0), 1)
```

### 4. Negative Lookahead

**Problem:** Current approach only adds positive labels. Some commits likely didn't need updates.

**Improvement:** If commit N changed components but no architecture update happened in the next 10 commits, label as likely-negative with confidence score.

Logic:
```python
# If meaningful changes but no update in lookahead window:
if has_meaningful_changes and not found_later_update:
    if lookahead_distance >= 10:  # Long enough window
        commit['should_have_updated'] = False  # Likely didn't need update
    else:
        commit['should_have_updated'] = None  # Uncertain
```

## Validation Strategy

**Important:** Do NOT validate lookahead results against the existing heuristic's predictions. That would be circular reasoning.

Instead, establish reference labels through:
1. **Manual review:** Sample 20-30 retrospectively-labeled commits and manually verify
2. **Interrater reliability:** Have 2+ humans independently label cases, measure agreement
3. **Time-based split:** Use early commits for training, later commits for validation

## Integration with LLM Approach

The lookahead-improved dataset is meant to be used for training/evaluating **both** approaches:

### String Heuristic (Current)
- Fast, deterministic, cheap
- Uses pattern matching on file types + message keywords
- Performance: ~0.82-0.85 F1 (estimated)

### LLM Classification (Future)
- Slow, non-deterministic, expensive
- Reads commit message + diff summaries, outputs binary prediction
- Performance: Unknown (to be measured)

**Key Point:** These are **independent predictors**, not validator and validatee. The goal is to compare them:

```
Reference Labels (from lookahead heuristics + manual review)
         ↓
    ┌────┴────┐
    ↓         ↓
Heuristic   LLM
Prediction  Prediction
    ↓         ↓
Evaluate    Evaluate
(P/R/F1)    (P/R/F1)
    ↓         ↓
  Compare performance
  ↓
  Choose best approach (or ensemble)
```

If the string heuristic performs nearly as well as the LLM, stick with the heuristic (faster/cheaper). If the LLM significantly outperforms, consider when the extra accuracy is worth the cost.

## Current Dataset Statistics

From `architecture_update_dataset.json`:
- Total commits analyzed: 18
- Architecture updated in commit: 3
- Retrospectively labeled as should-have-updated: 2
  - `98fb9711`: Changed 2 components, updated 1 commit later ✓ (confident)
  - `827e1833`: Changed 0 components, behavior keyword match ✗ (likely incorrect)

**Improvement needed:** The low confidence rate (50% of retrospective labels likely incorrect) suggests the lookahead logic needs refinement, particularly around semantic similarity and confidence scoring.

## Next Steps

1. **Implement semantic similarity checks** to reduce incorrect labels
2. **Add confidence scoring** and flag uncertain cases
3. **Manually review** all retrospectively-labeled commits (currently only 2, easy to do)
4. **Expand dataset** by analyzing more commits (currently only 18, increase to 100+)
5. **Document manual review process** so future labeling is consistent
6. **Train initial LLM classifier** on improved dataset
7. **Compare heuristic vs LLM** on held-out test set

## File References

- Dataset generator: `generate_architecture_dataset.py`
- Lookahead logic: `detect_retrospective_labels()` function (lines 213-262)
- Full dataset: `architecture_update_dataset.json`
- Training dataset: `architecture_update_training.json`
- Heuristic implementation: `scripts/check_architecture_update.py`
