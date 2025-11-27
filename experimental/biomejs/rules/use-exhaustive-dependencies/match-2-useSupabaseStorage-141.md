---
last_updated: 2025-11-27 10:48, 0b14126
---
# Match 2: useSupabaseStorage.js:141

## Code Reference
`src/hooks/useSupabaseStorage.js:141`

## Lint Message
"This hook does not specify its dependency on defaultValue"

## Analysis

The `useSupabaseStorage` hook takes `defaultValue` as a parameter (line 135) and uses it inside the `useEffect` at line 141:
- Line 144: `readValue(key, defaultValue)` - passed to the read function
- Lines 154-155: Used as fallback in the catch block

**Why adding `defaultValue` to deps would be problematic:**

1. **Referential instability**: If callers pass inline objects or arrays (e.g., `useSupabaseStorage('key', {})` or `useSupabaseStorage('key', [])`), a new reference is created on every render. Adding `defaultValue` to deps would cause the effect to re-run infinitely.

2. **Intentional design**: The `defaultValue` is semantically an "initial value" - it's meant to be used only on first mount/when the key changes. The hook's contract is: "load from storage once per key, using defaultValue only as a fallback if storage is empty or fails." Re-running the effect when `defaultValue` changes would violate this contract.

3. **No practical stale closure bug**: The `defaultValue` is only used as a fallback when storage read fails. In practice:
   - If the storage read succeeds, `defaultValue` is never used after the initial call
   - If `defaultValue` changes after mount, the stored/cached value is already loaded and takes precedence
   - The "staleness" here is intentional - you don't want to reset the loaded value just because someone changed the default

4. **Common React pattern**: Intentionally omitting "initial value" parameters from deps is a well-established pattern in React (similar to how `useState(initialValue)` only uses `initialValue` on first render).

**Note**: The same issue exists in the second `useEffect` at line 165 for the same reasons.

## Verdict
**FALSE POSITIVE**

## Confidence
High
