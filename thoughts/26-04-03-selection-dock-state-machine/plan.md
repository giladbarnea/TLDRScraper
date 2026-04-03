---
last_updated: 2026-04-03 20:40
---
# Plan: Selection dock action state machine + shared summary/digest sensitivity

## Scope map

Primary client files expected to change:
- `client/src/App.jsx`
- `client/src/components/SelectionActionDock.jsx`
- `client/src/components/ArticleCard.jsx`
- `client/src/hooks/useDigest.js`
- `client/src/hooks/useSupabaseStorage.js`
- potentially `client/src/index.css`

## Updated constraints from review

1. Dock state cannot rely on `results.payloads` because live state is in storage-backed caches/hooks.
2. Dock cannot open summary by instantiating a second `useSummary` instance. Overlay is rendered by `ArticleCard` instance only.
3. Batch operations should avoid per-article concurrent hook writes against the same date payload.
4. Digest’s current single-date mutation behavior must be aligned if dock depends on digest-driven summary status.

## Implementation strategy

### 1) Add shared article action event bus (single source for dock -> cards)

Introduce a lightweight module-level bus for article actions:
- `open-summary` for url
- `fetch-summary` for url / urls

`ArticleCard` subscribes (by url) and routes events into its existing `useSummary` instance:
- `open-summary` => `summary.expand()`
- `fetch-summary` => invoke fetch only if actionable (unknown/error), ignore loading/available

This preserves current overlay ownership and summary state machine while allowing dock actions to drive card-owned summary behavior.

### 2) Make dock state derive from live storage, not stale `results`

In `App.jsx`, add a hook that computes selected-article view model from current cache values:
- use selected IDs from `useInteraction`
- read the live payload(s) for dates in current results via a shared storage snapshot helper in `useSupabaseStorage`
- resolve selected articles from that snapshot each render

Derived facts:
- selected count
- single selected article (if one)
- single summary status
- summarize-each actionable count (`unknown` + `error` only)
- all summaries available (for selected)
- any summaries loading

### 3) Redesign `SelectionActionDock` as declarative action list

Replace fixed buttons with condition-driven action entries.

Always:
- Deselect
- Read
- Remove

Single select:
- Summarize/Open (label/icon swap to Open when status=available)
- Browse

Multi select:
- Digest
- Summarize Each (disabled when none actionable; visually inactive when all selected have summaries)

Also handle loading/error labels where relevant.

### 4) Implement batch read/remove as per-date grouped writes

In `App.jsx` orchestration, group selected articles by `issueDate`, and perform one payload update per date using `useSupabaseStorage` set function per date.

Do not loop through per-article `useArticleState()` instances.

### 5) Align digest side-effects for multi-date selections

Update `useDigest` so digest lifecycle mutations (`summary.loading`, restore, consumed mark read/remove) apply across all selected dates, not just target date.

Approach:
- resolve all involved dates from selected descriptors
- for each date payload key, apply grouped article URL updates
- keep digest artifact stored under target date as today

This guarantees dock summary sensitivity to digest-driven transitions across selected items.

### 6) Browse/open behavior details

- Browse: single selected article URL opens in new tab.
- Open: dispatch shared `open-summary` event for selected URL.
- If zen lock is occupied, existing behavior no-ops naturally.

### 7) Verification

- `cd client && npm run build`
- manual run:
  - select 1 unknown => Summarize -> loading -> Open
  - select 1 available => Open immediately
  - select N mixed statuses => Summarize Each active only for unknown/error
  - select N all available => Summarize Each inactive
  - digest with multi-date selection updates statuses and dock conditions
  - read/remove batch actions apply across selected dates

### 8) Screenshot

Take updated screenshot of dock states (single + multi selection) if browser screenshot tooling is available.
