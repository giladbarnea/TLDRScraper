---
status: completed
last_updated: 2026-05-11 09:37
---

# Unified Feed Read Model

Eliminated the client's two competing read models for article state — payload-shaped props flowing down the component tree vs. the live `articleStore`. The root cause of several subtle bugs (missing articles after scrape, stale grouped UI, digest identity confusion) was that authority was never encoded strongly enough in the API surface.

**Decision:** `articleStore` becomes the sole client authority. `ArticleKey = date::url` replaces URL-as-identity everywhere. Components render store keys and selectors only. `useFeedLoader` becomes a command hook (no `results.payloads`). `sessionStorage` feed cache deleted — Supabase + `/api/scrape` already provide the useful cache.

**Implementation:** One-shot cutover rather than the planned 9-step migration (two read models during migration is the anti-pattern we're removing). Key changes:

- `articleStore.js` — extended with `feed`, `daysByDate`, `articlesByKey`; added `ingestFeedPayloads`/`ingestDayPayload` single ingestion boundary; new selectors: `useFeedStatus`, `useVisibleDates`, `useDayView`, `useNewsletterView`, `useArticleCard`, `useArticleLifecycle`
- `useFeedLoader.js` — command-only; sessionStorage cache removed
- Component tree — `Feed → CalendarDay → NewsletterDay → ArticleList → ArticleCard` all key-driven, no payload props
- Removed: `urlToArticleKey`, `dayArticleSummaries`, `dayLifecycleListeners`, `RemovedOrderSlot`, `mergePreservingLocalState`

**Follow-up (PR 661):** Digest collapse was the last URL-as-identity site. Fixed by storing article keys (not URLs) on the digest record. Seeded a real cross-date duplicate in Supabase to verify.

**Drift:** Server-side summary persistence was missing from the plan. Summaries vanished on refresh because they were only written to client memory. Fixed by having `/api/summarize-url` accept `issue_date`, call `persist_article_summary` with conflict-retry, and return the canonical payload. Client ingests via `ingestDayPayload` — no path where the client thinks a summary exists but Supabase doesn't.
