---
last_updated: 2025-11-27 10:48, 0b14126
---
# Match 3: useSupabaseStorage.js:165

## Code Reference
`src/hooks/useSupabaseStorage.js:165`

## Lint Message
"This hook does not specify its dependency on defaultValue"

## Analysis

The second useEffect (lines 165-176) sets up a subscription to storage changes:

```javascript
useEffect(() => {
  const handleChange = () => {
    readValue(key, defaultValue).then(newValue => {
      setValue(newValue)
      valueRef.current = newValue
    }).catch(err => {
      console.error(`Failed to reload storage value for ${key}:`, err)
    })
  }

  return subscribe(key, handleChange)
}, [key])
```

### What it does
This effect subscribes to storage change events for the given `key`. When another part of the app writes to the same key (via `emitChange`), this listener re-reads the value and updates local state.

### Should `defaultValue` be in deps?

**No, for the same reasons as the first useEffect:**

1. **`defaultValue` is only a fallback for error cases**: Looking at `readValue()`, `defaultValue` is only returned when:
   - We're in SSR (`typeof window === 'undefined'`)
   - The API call fails (line 78 catch block)

   In both cases, this is a fallback for exceptional circumstances, not the happy path.

2. **Re-subscribing on `defaultValue` change is wasteful**: If `defaultValue` changed (e.g., from `null` to `[]`), the subscription mechanism doesn't need to change. The subscription is based on `key`, not `defaultValue`. Re-subscribing would unsubscribe and re-subscribe to the same key for no functional benefit.

3. **Stale closure concern is minimal**: Even if `defaultValue` changes, the only impact is that on a failed re-read, we'd use the old default. In practice:
   - `defaultValue` typically doesn't change (it's a constant passed to the hook)
   - If it did change, the first useEffect (lines 141-163) would likely re-trigger and load fresh data anyway
   - The error case where this matters is already a degraded state

4. **Consistency with the first useEffect**: Both useEffects intentionally omit `defaultValue` for the same reason - it's an initial/fallback value, not a dependency that should trigger re-execution.

5. **Potential infinite loop risk**: If `defaultValue` is an object/array literal passed inline (e.g., `useSupabaseStorage('key', [])`), adding it to deps would cause infinite re-subscriptions since `[]` creates a new reference on every render.

## Verdict
**FALSE POSITIVE**

## Confidence
High

The omission of `defaultValue` from the dependency array is intentional and correct. The subscription should only be re-established when the `key` changes, not when a fallback value changes. Adding `defaultValue` to deps would cause unnecessary re-subscriptions and potential infinite loops without fixing any real bug, since `defaultValue` is only used as a fallback in error scenarios.
