---
name: Context Menu Implementation Round 1
done: commitsha
last_updated: 2026-04-18 11:11, dcedec8
---

# Context Menu Implementation Round 1

## Iteration 1 Summary

"See client files abc, checked todo items in ../xyz, and doc updates 1,2,3 in files foo bar baz"

---

## Tackling the increased complexity this iteration introduced

Coupling patterns cause this complexity. Apply these principles:

1. **Delegate to primitives.** Mobile selection, outside-click, focus, positioning, and ARIA are solved in Radix or Floating UI. Hand-rolling requires ref-juggling and global listeners. Adopt battle-tested primitives to reduce complexity.
2. **Co-locate the contract.** The `data-overlay-content` marker and document-level listeners split logic across files. Use a compound component (e.g., `<SelectableSurface>`) to own both the scroll area and menu via context. Replace DOM marking with component composition.
3. **Use a stack, not arbitration.** The `Escape`, `stopImmediatePropagation`, and `defaultPrevented` dance happens when listeners compete. Use a modal/focus stack where only the topmost layer receives `Escape`. Standard `<Dialog>` primitives provide this.
4. **Make state explicit.** Replace `openedBySelectionRef`, `touchActive`, and interleaved `selectionchange`/`touchend` with a named enum (`idle` | `armed` | `open`) and a reducer. Consolidates implicit transitions across scattered listeners into one readable table.
5. **Split desktop and mobile.** Unifying right-click and selection-then-touch creates timing issues. Use two distinct, narrow hooks composed by the surface instead of one complex, generalized hook.

**Meta-principle:** Boundary complexity (DOM and event system) evades type-checking and unit tests. Pulling boundaries into a single owner (component or library) converts distributed contracts into local implementation details.