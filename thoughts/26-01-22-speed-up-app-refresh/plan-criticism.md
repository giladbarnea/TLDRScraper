---
last_updated: 2026-01-23 14:59
---
# Review: Scrape-First Source of Truth (Option 1) Implementation Plan

The plan (./plan.md) proposes removing one part of the old coupling to storage: making a server request on app load for each CalendarDay’s corresponding storage key. That’s indeed redundant as the plan concludes, and this behavior should be removed.

But the plan doesn’t address a second, crucial part of the system that needs to be preserved. When a user changes an individual card’s or newsletter’s state—e.g., by removing it or marking it as read—the binding to daily storage mattered. Even though the UI uses optimistic updates, once an article was removed a POST request was sent to the server to persist the new state in the database. The response to that request was then treated as the UI’s source of truth. Ideally it matched the optimistic update so the user didn’t notice anything, but the mechanism was still essential.

Executing the plan in its current revision would mean that CalendarDay derives articles directly and only from the static payload, so it no longer updates when useArticleState writes read/removed changes back to the daily payload in Supabase. In practice, after a user marks an article as read/removed, the per-day ReadStatsBadge, the allArticlesRemoved folding logic, and the ArticleList ordering still reflect the stale scrape response until the next /api/scrape refresh—even though individual cards show the updated state. This is a regression from the previous storage subscription: if per-article state is still persisted, CalendarDay needs a reactive source (or a lifted state update) to keep list-level UI consistent.

Bottom line: these two aspects of the storage entanglement need to be separated. The first—“fetching daily storage on refresh”—should be cut, but the second—“updating storage on article state change”—needs to remain.