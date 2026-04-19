---
name: code-simplification
description: Simplify code for clarity. Use when refactoring without changing behavior. Use when working code is hard to read, maintain, or extend. Use to remove unnecessary complexity during code review.
last_updated: 2026-04-19 05:08
---

# Code Simplification

> Inspired by the [Claude Code Simplifier plugin](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/code-simplifier/agents/code-simplifier.md). Adapted as a model-agnostic, process-driven skill.

## Overview

Simplify code to reduce complexity. Preserve exact behavior. Goal is readability, not line count. Metric: "Would a new team member understand this faster?"

## When to Use

- Feature works and tests pass, but implementation is heavy.
- Code review flags readability or complexity.
- Encountering deeply nested logic, long functions, or unclear names.
- Refactoring rushed code.
- Consolidating scattered related logic.
- Merging introduced duplication or inconsistency.

**When NOT to use:**

- Code is already clean.
- Code is not understood yet. Comprehend first.
- Performance-critical code where simplification slows execution.
- Module planned for rewrite.

## The Five Principles

### 1. Preserve Behavior Exactly

Change expression, not action. Inputs, outputs, side effects, error behavior, and edge cases must remain identical. Do not simplify if unsure.

```
ASK BEFORE EVERY CHANGE:
→ Does this produce the same output for every input?
→ Does this maintain the same error behavior?
→ Does this preserve the same side effects and ordering?
→ Do all existing tests still pass without modification?
```

### 2. Follow Project Conventions

Match codebase consistency. Do not impose external preferences. Before simplifying:

```
1. Read CLAUDE.md / project conventions
2. Study how neighboring code handles similar patterns
3. Match the project's style for:
   - Import ordering and module system
   - Function declaration style
   - Naming conventions
   - Error handling patterns
   - Type annotation depth
```

Breaking consistency is churn, not simplification.

### 3. Prefer Clarity Over Cleverness

Prefer explicit over compact if compact requires mental pause.

```typescript
// UNCLEAR: Dense ternary chain
const label = isNew ? 'New' : isUpdated ? 'Updated' : isArchived ? 'Archived' : 'Active';

// CLEAR: Readable mapping
function getStatusLabel(item: Item): string {
  if (item.isNew) return 'New';
  if (item.isUpdated) return 'Updated';
  if (item.isArchived) return 'Archived';
  return 'Active';
}
```

```typescript
// UNCLEAR: Chained reduces with inline logic
const result = items.reduce((acc, item) => ({
  ...acc,
  [item.id]: { ...acc[item.id], count: (acc[item.id]?.count ?? 0) + 1 }
}), {});

// CLEAR: Named intermediate step
const countById = new Map<string, number>();
for (const item of items) {
  countById.set(item.id, (countById.get(item.id) ?? 0) + 1);
}
```

### 4. Maintain Balance

Avoid over-simplification traps:
- **Aggressive inlining**: Removes named concepts, reducing readability.
- **Combining unrelated logic**: Merges simple functions into complex ones.
- **Removing abstraction**: Destroys intended extensibility or testability.
- **Optimizing line count**: Prioritizes size over comprehension.

### 5. Scope to What Changed

Limit simplifications to modified code. Avoid unscoped refactors to prevent diff noise and regressions. Broaden scope only if asked.

## The Simplification Process

### Step 1: Understand Before Touching (Chesterton's Fence)

Understand existing code before modifying. Identify original intent before changing.

```
BEFORE SIMPLIFYING, ANSWER:
- What is this code's responsibility?
- What calls it? What does it call?
- What are the edge cases and error paths?
- Are there tests that define the expected behavior?
- Why might it have been written this way? (Performance? Platform constraint? Historical reason?)
- Check git blame: what was the original context for this code?
```

If unanswered, read context first.

### Step 2: Identify Simplification Opportunities

Scan for structural signals:

| Pattern | Signal | Simplification |
|---------|--------|----------------|
| Deep nesting (3+ levels) | Hard to follow control flow | Extract guard clauses or helpers |
| Long functions (50+ lines) | Multiple responsibilities | Split into focused, named functions |
| Nested ternaries | Requires mental stack | Replace with if/else, switch, lookup table |
| Boolean parameter flags | `doThing(true, false, true)` | Use options objects or separate functions |
| Repeated conditionals | Same `if` check everywhere | Extract to named predicate function |

Scan for naming issues:

| Pattern | Signal | Simplification |
|---------|--------|----------------|
| Generic names | `data`, `result`, `temp`, `val` | Rename to describe content (`userProfile`) |
| Abbreviated names | `usr`, `cfg`, `btn`, `evt` | Use full words (except universal like `id`, `url`) |
| Misleading names | `get` mutates state | Rename to reflect behavior |
| "What" comments | `// calc` above `x++` | Delete comment. Code is clear |
| "Why" comments | `// Retry due to flaky API` | Keep. Carries intent code cannot express |

Scan for redundancy:

| Pattern | Signal | Simplification |
|---------|--------|----------------|
| Duplicated logic | Same 5+ lines repeated | Extract to shared function |
| Dead code | Unreachable blocks, unused vars | Remove after verification |
| Useless abstraction | Value-less wrapper | Inline wrapper, call underlying directly |
| Over-engineering | Factory-for-a-factory | Replace with direct approach |
| Redundant types | Casting inferred types | Remove assertion |

### Step 3: Apply Changes Incrementally

Apply one simplification at a time. Run tests after each. Separate refactoring PRs from feature PRs.

```
FOR EACH SIMPLIFICATION:
1. Make change
2. Run tests
3. Pass → commit or continue
4. Fail → revert and rethink
```

Do not batch untested changes. Fast isolate failures.

**The Rule of 500:** Use automation (codemods, AST transforms) for >500-line refactors. Manual edits at scale cause errors.

### Step 4: Verify the Result

Evaluate complete change:
- Is code easier to understand?
- Does pattern match codebase?
- Is diff clean?
- Would a team member approve?

Revert if harder to understand or review.

## Language-Specific Guidance

### TypeScript / JavaScript

```typescript
// SIMPLIFY: Unnecessary async wrapper
// Before
async function getUser(id: string): Promise<User> {
  return await userService.findById(id);
}
// After
function getUser(id: string): Promise<User> {
  return userService.findById(id);
}

// SIMPLIFY: Verbose conditional assignment
// Before
let displayName: string;
if (user.nickname) {
  displayName = user.nickname;
} else {
  displayName = user.fullName;
}
// After
const displayName = user.nickname || user.fullName;

// SIMPLIFY: Manual array building
// Before
const activeUsers: User[] = [];
for (const user of users) {
  if (user.isActive) {
    activeUsers.push(user);
  }
}
// After
const activeUsers = users.filter((user) => user.isActive);

// SIMPLIFY: Redundant boolean return
// Before
function isValid(input: string): boolean {
  if (input.length > 0 && input.length < 100) {
    return true;
  }
  return false;
}
// After
function isValid(input: string): boolean {
  return input.length > 0 && input.length < 100;
}
```

### Python

```python
# SIMPLIFY: Verbose dictionary building
# Before
result = {}
for item in items:
    result[item.id] = item.name
# After
result = {item.id: item.name for item in items}

# SIMPLIFY: Nested conditionals with early return
# Before
def process(data):
    if data is not None:
        if data.is_valid():
            if data.has_permission():
                return do_work(data)
            else:
                raise PermissionError("No permission")
        else:
            raise ValueError("Invalid data")
    else:
        raise TypeError("Data is None")
# After
def process(data):
    if data is None:
        raise TypeError("Data is None")
    if not data.is_valid():
        raise ValueError("Invalid data")
    if not data.has_permission():
        raise PermissionError("No permission")
    return do_work(data)
```

### React / JSX

```tsx
// SIMPLIFY: Verbose conditional rendering
// Before
function UserBadge({ user }: Props) {
  if (user.isAdmin) {
    return <Badge variant="admin">Admin</Badge>;
  } else {
    return <Badge variant="default">User</Badge>;
  }
}
// After
function UserBadge({ user }: Props) {
  const variant = user.isAdmin ? 'admin' : 'default';
  const label = user.isAdmin ? 'Admin' : 'User';
  return <Badge variant={variant}>{label}</Badge>;
}

// SIMPLIFY: Prop drilling through intermediate components
// Before — consider context or composition. Judgment call — flag it, do not auto-refactor.
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Working, leave it" | Hard-to-read working code is hard to fix later. Simplify now. |
| "Fewer lines simpler" | Simplicity is comprehension speed, not line count. |
| "Simplify unrelated code" | Creates noisy diffs and risks regressions. Stay focused. |
| "Self-documenting types" | Types document structure, not intent. Well-named function explains *why*. |
| "Useful later" | Complexity without value. Remove speculative abstractions. |
| "Original author reason" | Apply Chesterton's Fence via git blame. Complexity often results from rushed iterations. |
| "Refactor with feature" | Separate refactoring. Mixed changes complicate review and revert. |

## Red Flags

- Tests require modification (behavior changed).
- "Simplified" code is longer or harder to follow.
- Renamed to external preference, not project convention.
- Removed error handling for cleanliness.
- Simplified without understanding.
- Batched simplifications in one massive commit.
- Refactored out of scope without request.

## Verification

After simplification pass:
- [ ] Tests pass unmodified.
- [ ] Build succeeds without new warnings.
- [ ] Linter/formatter passes without style regressions.
- [ ] Changes are reviewable and incremental.
- [ ] Diff is clean. No unrelated changes.
- [ ] Code follows project conventions.
- [ ] Error handling retained.
- [ ] Dead code removed.
- [ ] Team member or review agent approves as improvement.
