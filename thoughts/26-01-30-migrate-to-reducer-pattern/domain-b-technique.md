# Domain B technique suggestion (summary data)

## Goal
Propose a low-friction reducer pattern for the summary data domain (`unknown` → `loading` → `available` / `error`) that could fit into the existing ArticleCard reducer ecosystem without over-coupling.

## Suggested technique: command-returning reducer with request tokens

**High-level idea**: keep the summary data reducer closed and pure, but have it emit commands that include a `requestToken` (or `requestId`). The runtime would execute the command, then include that token on the response event so the reducer can ignore stale responses.

### Why this might help
- It could make the reducer resilient to rapid user actions (tap → cancel → tap) without adding guard clauses to UI handlers.
- It might reduce race conditions when multiple summary requests fire for the same article (e.g., retry after error).
- It could allow you to keep summary data state orthogonal to summary view state (Domain C), while still enabling a mediator to open the view on `SUMMARY_AVAILABLE`.

## Proposed state shape (example)
```
{
  status: 'unknown' | 'loading' | 'available' | 'error',
  requestToken: string | null,
  markdown: string | null,
  errorMessage: string | null,
  checkedAt: string | null
}
```

## Proposed events
- `SUMMARY_REQUESTED` (input)
- `SUMMARY_LOAD_SUCCEEDED` (outcome)
- `SUMMARY_LOAD_FAILED` (outcome)
- `SUMMARY_RESET` (input)

## Reducer sketch (pseudo)
```
function reduceSummaryData(state, event) {
  if (event.type === 'SUMMARY_REQUESTED') {
    const requestToken = createToken()
    return {
      state: {
        ...state,
        status: 'loading',
        requestToken,
        errorMessage: null
      },
      commands: [{ type: 'FETCH_SUMMARY', requestToken }]
    }
  }

  if (event.type === 'SUMMARY_LOAD_SUCCEEDED') {
    if (event.requestToken !== state.requestToken) return { state, commands: [] }
    return {
      state: {
        ...state,
        status: 'available',
        markdown: event.markdown,
        checkedAt: event.checkedAt,
        requestToken: null
      },
      commands: []
    }
  }

  if (event.type === 'SUMMARY_LOAD_FAILED') {
    if (event.requestToken !== state.requestToken) return { state, commands: [] }
    return {
      state: {
        ...state,
        status: 'error',
        errorMessage: event.errorMessage,
        requestToken: null
      },
      commands: []
    }
  }

  if (event.type === 'SUMMARY_RESET') {
    return { state: { status: 'unknown' }, commands: [] }
  }

  return { state, commands: [] }
}
```

## Hypothesized outcomes
- The runtime could safely fire overlapping fetches and the reducer would likely accept only the latest response, which may reduce accidental state regressions.
- If the mediator chooses to open the summary view on `SUMMARY_LOAD_SUCCEEDED`, you might keep the view domain “closed” while still allowing a smooth UX.
- This approach may make retry flows more predictable because `SUMMARY_REQUESTED` always resets the request token and clears prior error state.

## Potential trade-offs
- You may need to plumb `requestToken` through `useSummary` and the fetch handler, which could add a small amount of wiring.
- If you already dedupe requests elsewhere, the token check might be redundant, though it could still act as a safety net.

## Next step suggestion
If this seems useful, I would consider prototyping it inside `useSummary` with a single ArticleCard before rolling it out more broadly. That might surface any subtle edge cases in the existing cache/merge logic.
