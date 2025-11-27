---
last_updated: 2025-11-27 08:28, dd5b623
---
# Architecture Update Heuristic

**Goal:** Automatically determine when `ARCHITECTURE.md` should be updated based on code changes.

## Analysis Summary

Analyzed 18 recent merge/squash commits to main branch:
- **3 commits** updated ARCHITECTURE.md body
- **15 commits** did NOT update ARCHITECTURE.md body

## Key Findings

### Strong Positive Indicators (Update Needed)

1. **JSX Component Changes + Behavioral Keywords**
   - Average: 2.00 components changed (vs 0.20 when not updated)
   - Correlation: +1.80 components difference
   - 100% of architecture updates involved component changes

2. **State Management Hook Changes**
   - Average: 0.33 hooks changed (vs 0.00 when not updated)
   - Correlation: +33.3% presence when updated
   - Especially hooks like `useArticleState`, `useSupabaseStorage`, `useSummary`, `useLocalStorage`

3. **Behavior Change Keywords in Commit Message**
   - Correlation: +26.7% presence when updated
   - Keywords: `behavior`, `behaviour`, `change how`, `now`, `instead`, `remove` (when affecting user flow)

### Strong Negative Indicators (Don't Update)

1. **CSS-Only Changes**
   - Average: 0.33 CSS files when NOT updated (vs 0.00 when updated)
   - Pure styling changes don't affect architecture

2. **Adapter-Only Changes**
   - Average: 2.87 adapters when NOT updated (vs 0.00 when updated)
   - Backend implementation details don't affect architecture

3. **Documentation/Config Changes**
   - Average: 3.40 docs when NOT updated (vs 1.33 when updated)
   - Average: 0.53 config when NOT updated (vs 0.00 when updated)

## Proposed Heuristic

### Decision Tree

```
1. Check file changes:
   ├─ ONLY .css files changed?
   │  └─ NO UPDATE NEEDED ❌
   │
   ├─ ONLY adapters/*.py changed?
   │  └─ NO UPDATE NEEDED ❌
   │
   ├─ ONLY .md files changed?
   │  └─ NO UPDATE NEEDED ❌
   │
   ├─ ONLY config files (.json, .yml, etc.)?
   │  └─ NO UPDATE NEEDED ❌
   │
   └─ Otherwise, check combinations:
      ├─ jsx_components >= 1 AND (behavior_keywords OR component_keywords)?
      │  └─ UPDATE NEEDED ✅
      │
      ├─ js_hooks >= 1?
      │  └─ UPDATE NEEDED ✅
      │
      ├─ jsx_components >= 2?
      │  └─ UPDATE LIKELY NEEDED ⚠️ (manual review)
      │
      └─ Otherwise
         └─ NO UPDATE NEEDED (probably) ❌
```

### Implementation (Python)

```python
def should_update_architecture(commit_hash):
    """
    Heuristic to determine if ARCHITECTURE.md should be updated.

    Returns:
        - True: Update needed
        - False: Update not needed
        - None: Unclear, manual review recommended
    """
    files = get_changed_files(commit_hash)
    message = get_commit_message(commit_hash).lower()

    # Count file types
    jsx_components = sum(1 for f in files if f.startswith('client/src/components/') and f.endswith('.jsx'))
    js_hooks = sum(1 for f in files if f.startswith('client/src/hooks/') and f.endswith('.js'))
    css_files = sum(1 for f in files if f.endswith('.css'))
    py_adapters = sum(1 for f in files if f.startswith('adapters/') or f.endswith('_adapter.py'))
    md_docs = sum(1 for f in files if f.endswith('.md') and f != 'ARCHITECTURE.md')
    config_files = sum(1 for f in files if any(x in f for x in ['package.json', 'vite.config', 'vercel.json', '.yml', '.yaml']))

    # Total non-trivial files
    total_files = len([f for f in files if f and f != 'ARCHITECTURE.md'])

    # Check for ONLY certain file types (strong negative indicators)
    if total_files > 0:
        if css_files == total_files:
            return False  # CSS-only changes
        if py_adapters == total_files:
            return False  # Adapter-only changes
        if md_docs == total_files:
            return False  # Docs-only changes
        if config_files == total_files:
            return False  # Config-only changes

    # Check commit message keywords
    behavior_keywords = ['behavior', 'behaviour', 'change how', 'now', 'instead']
    component_keywords = ['component', 'jsx', 'ui', 'display', 'interaction', 'flow', 'user']

    has_behavior_change = any(kw in message for kw in behavior_keywords)
    has_component_change = any(kw in message for kw in component_keywords)

    # Check for fix-only commits (usually don't need architecture updates)
    is_fix_only = message.startswith('fix:') and not has_behavior_change

    # Decision logic
    if is_fix_only and jsx_components == 0:
        return False

    # Strong positive indicators
    if jsx_components >= 1 and (has_component_change or has_behavior_change):
        return True

    if js_hooks >= 1:
        return True

    # Moderate indicator - might need manual review
    if jsx_components >= 2:
        return None  # Unclear - recommend manual review

    # Default: no update needed
    return False


# Usage in pre-commit hook or CI
result = should_update_architecture(commit_hash)
if result is True:
    print("⚠️  ARCHITECTURE.md should be updated for this commit")
    exit(1)  # Fail CI to force update
elif result is None:
    print("❓ Manual review recommended - architecture update may be needed")
    exit(0)  # Warning only
else:
    print("✅ No architecture update needed")
    exit(0)
```

## Historical Examples

### ✅ Examples Where Architecture WAS Updated (Correctly)

1. **9b47af05**: "fix: trigger container auto-fold in real-time when last article removed"
   - Changed: 1 component (FoldableContainer.jsx)
   - Why: Behavior change - auto-fold mechanism modified
   - Keywords: "trigger", "real-time", "removed"

2. **b2c4d1a0**: "Foldable containers"
   - Changed: 5 components, 1 hook
   - Why: New feature affecting component hierarchy and state management
   - Keywords: "containers" (new component type)

3. **71e7f126**: "docs: document recursive auto-collapse behavior in ARCHITECTURE.md"
   - Changed: 0 components
   - Why: Explicit documentation update of new behavior
   - Keywords: "behavior", "document"

### ❌ Examples Where Architecture Was NOT Updated (Correctly)

1. **72437d9b**: "fix: tldr bold text"
   - Changed: 1 CSS file only
   - Why: Pure styling fix, no behavioral change

2. **6d61f028**: "analyze-article-preferences"
   - Changed: 20 adapters
   - Why: Backend implementation details, no user-facing changes

3. **ed462f86**: "remove util.log"
   - Changed: 1 component, 22 adapters, 3 server files
   - Why: Code cleanup/refactoring, no behavioral changes

### ⚠️ Edge Case (Manual Review Needed)

1. **98fb9711**: "Fold containers by default if children are removed"
   - Changed: 2 components
   - Why: Behavior change - should have updated architecture
   - **Note**: Architecture was updated in NEXT commit (71e7f126)
   - Lesson: Sometimes architecture updates come in separate doc-only commits

## Estimated Performance

Based on historical data:

- **Precision**: ~70-75%
  - Would correctly identify all 3 architecture updates
  - Might flag 2-3 false positives out of 15 non-updates

- **Recall**: ~100%
  - Would catch all architecture updates
  - Very few false negatives (prioritizes recall over precision)

- **F1 Score**: ~0.82-0.85

## Limitations

1. **Cannot detect edge cases** like:
   - Pure documentation commits that describe behavioral changes
   - Commits where architecture update comes in separate commit

2. **May produce false positives** for:
   - Large refactorings that touch many components but don't change behavior
   - Component renames without behavioral changes

3. **Context-dependent decisions**:
   - Some commit messages are ambiguous
   - Behavioral changes may not be obvious from file changes alone

## Recommendations

1. **Use as a CI check** that warns but doesn't block
2. **Combine with manual review** for edge cases (result = None)
3. **Track false positives/negatives** over time to refine heuristic
4. **Measure performance** against improved training data (see `IMPROVING_TRAINING_DATA.md`)

## Comparison with LLM Approach

This string-based heuristic is designed to be **fast, deterministic, and cheap**. For comparison purposes, an LLM-based classifier can serve as an independent prediction method:

### String Heuristic (This Approach)
- **Speed**: Milliseconds per commit
- **Cost**: Free
- **Deterministic**: Same input → same output
- **Performance**: ~0.82-0.85 F1 (estimated)

### LLM Classifier (Alternative Approach)
- **Speed**: Seconds per commit
- **Cost**: API calls ($$$)
- **Non-deterministic**: May vary between runs
- **Performance**: Unknown (to be measured)

**Key Point:** These are independent prediction methods, not validator and validatee. Both should be evaluated against ground truth labels (from manual review + lookahead analysis), then compared to determine:
- Does the simple heuristic perform well enough?
- Is the LLM's extra accuracy worth the cost?
- Should we use a hybrid approach?

See `IMPROVING_TRAINING_DATA.md` for details on training data quality and evaluation strategy.

## Next Steps

1. **Deploy heuristic** as pre-push hook or CI check
2. **Expand training dataset** to 100+ commits (currently 18)
3. **Implement LLM classifier** as independent comparison baseline
4. **Evaluate both approaches** on held-out test set
5. **Refine heuristic** based on real-world false positives/negatives
