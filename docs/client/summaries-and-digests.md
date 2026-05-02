---
name: client/summaries-and-digests
description: Client-side summary and digest data vs view state management.
last_updated: 2026-05-02 11:36
---
# Client: Summaries and Digests

[→ Server: Summaries](../server/summaries.md) | [→ State Machines: Articles & Summaries](../state-machines/articles-and-summaries.md)

## Summary (Domain B + View State)

Summary management separates **data state** (reducer: `unknown → loading → available/error`) from **view state** (simple `useState` for expanded/collapsed). The `useSummary` hook orchestrates both. See [State Machines: Articles and Summaries](../state-machines/articles-and-summaries.md#2-summary-data) for the data state machine.

**Key modules:** `reducers/summaryDataReducer.js`, `hooks/useSummary.js`, `lib/markdownUtils.js` (markdown→HTML conversion with KaTeX support), `lib/zenLock.js` (mutual-exclusion lock), `lib/requestUtils.js` (request tokens)

---
