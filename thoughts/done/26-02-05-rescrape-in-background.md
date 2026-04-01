---
last_updated: 2026-04-01 18:05
description: Two-phase feed loading: immediate render from cache + background rescrape/merge.
---
# Background Rescrape

## Problem
Initial page load was blocked by `POST /api/scrape` for "today's" content (3-15s delay).

## Solution
Implemented a two-phase loading strategy in `App.jsx`:
1. **Phase 1 (Immediate)**: Fetch cached payloads via `getDailyPayloadsRange` (~100ms) and render immediately.
2. **Phase 2 (Background)**: Fire `scrapeNewsletters` concurrently. Upon completion, use `mergeIntoCache` (exported from `useSupabaseStorage.js`) to apply fresh results to the live UI via pub/sub.

## Key Primitives
- `mergeIntoCache(key, mergeFn)`: Updates shared `readCache` and emits change to all hook subscribers.
- `mergePreservingLocalState`: Client-side merge that overlays server results with local optimistic user state (`read`, `removed`, `tldr`).

## Gotcha (2026-02-15)
Fixed a bug where `article.issueDate` mismatch after merge caused click failures. Authority for `issueDate` was moved to `CalendarDay` to ensure key consistency.
