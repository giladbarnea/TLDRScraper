---
name: client/summaries-and-digests
description: Client-side summary and digest data vs view state management.
last_updated: 2026-05-05 06:38, 36614cc
---
# Client: Summaries and Digests

[→ Server: Summaries](../server/summaries.md) | [→ State Machines: Articles & Summaries](../state-machines/articles-and-summaries.md)

## Summary (Domain B + View State)

Summary management separates **data state** (`unknown → loading → available/error`) from **view state** (`expandedView`). Both now live on the article slice in `articleStore`; `useSummary` subscribes to that slice and returns stable command closures for fetch, expand, collapse, and toggle. See [State Machines: Articles and Summaries](../state-machines/articles-and-summaries.md#2-summary-data) for the data state machine.

**Key modules:** `reducers/summaryDataReducer.js`, `hooks/useSummary.js`, `store/articleStore.js`, `lib/dailyPayloadMutations.js`, `lib/zenLock.js` (mutual-exclusion lock), `lib/requestUtils.js` (request tokens)

Markdown conversion is intentionally kept out of the hot subscription hook. Overlay surfaces memoize rendered HTML with `lib/markdownUtils.js`: `ZenModeOverlay`, `DigestOverlay`, and `ElaborationPreview`.

Digest uses the same store and mutation boundary. `useDigest` reads the target day slice, marks participating articles with grouped batch patches, writes digest status with `queueDailyPayloadPatch()`, and opens `DigestOverlay` through the shared zen lock.

---
