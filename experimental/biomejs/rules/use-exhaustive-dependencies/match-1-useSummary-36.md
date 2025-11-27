---
last_updated: 2025-11-27 10:48, 0b14126
---
# Match 1: useSummary.js:36

## Code Reference
`src/hooks/useSummary.js:36`

## Lint Message
"This hook specifies more dependencies than necessary: type"

## Analysis

The `useMemo` hook at line 36-42:

```javascript
const buttonLabel = useMemo(() => {
  if (isLoading) return 'Loading...'
  if (expanded) return 'Expanded'
  if (isAvailable) return 'Available'
  if (isError) return 'Retry'
  return 'TLDR'
}, [isLoading, expanded, isAvailable, isError, type])
```

The `type` parameter comes from the function signature `useSummary(date, url, type = 'tldr')` with a default value of `'tldr'`.

Looking at the memoized computation:
1. The function body does **not** reference `type` anywhere
2. It only uses: `isLoading`, `expanded`, `isAvailable`, `isError`
3. The hardcoded return value `'TLDR'` is a string literal, not derived from `type`

The lint is correct: `type` is included in the dependency array but is never used inside the memoized callback. The memoized value will be recalculated when `type` changes, but since `type` doesn't affect the computation, this is unnecessary.

One might argue that if `type` changes, the button label *should* change (e.g., maybe it should return `type.toUpperCase()` instead of hardcoded `'TLDR'`). However, that would be a feature request, not a justification for keeping `type` in the deps. As written, the code doesn't use `type` in this computation.

Note: The related values `isAvailable`, `isError`, etc. are derived from `data`, which is derived from `article?.[type]`. So when `type` changes, those intermediate values would already change and trigger a recomputation. Therefore, including `type` directly is redundant even from a semantic perspective.

## Verdict
**TRUE POSITIVE**

## Confidence
High
