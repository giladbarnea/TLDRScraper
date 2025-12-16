---
created: 2025-12-16
last_updated: 2025-12-16 15:44
---
# Fix Cache-Scrape Edge Case for Today

## Problem

When a user scrapes today's date, the results are cached. If sources publish new articles later that day and the user scrapes again, the new articles are not detected. The client-side cache check prevents the server from being called at all.

## Current Behavior

1. Client checks if date is cached via `isRangeCached()`
2. If cached, returns stored data immediately — server never called
3. Cache check only verifies row existence, not freshness
4. New intra-day articles are invisible to the user

## Desired Behavior

1. Scrape requests that include today always reach the server
2. Server checks its own cache for today's existing URLs
3. Server excludes cached URLs from external fetches (avoids redundant network calls)
4. Server returns only new articles
5. Client merges new articles with existing cache, preserving user state (read, removed, TLDR)

## Invariants

- If a URL is already cached, its content is not re-fetched
- If a TLDR is already generated, it is not regenerated
- User state (read, removed, tldrHidden) is never lost on re-scrape
- Past dates (not today) retain current cache-first behavior
- Client remains unaware of URL-level caching — server handles it internally

## What We're NOT Doing

- No client-to-server round-trip of cached URLs
- No changes to the merge logic (already correct)
- No changes to TLDR generation flow
- No timestamp-based cache invalidation
- No changes to past-date caching behavior

## Changes Required

### Client: `client/src/lib/scraper.js`

**Location**: `isRangeCached()` function

**Behavior change**: If any date in the requested range is today, return `false` (forcing server call). All other logic unchanged.

### Server: `tldr_service.py`

**Location**: `scrape_newsletters_in_date_range()` function, before calling `scrape_date_range()`

**Behavior change**: If today is within the requested date range, load today's cached payload from storage. Extract cached article URLs and merge them into `excluded_urls`. The existing `excluded_urls` parameter already threads through to adapters — no downstream changes needed.

## Verification

1. Scrape today (fresh) — articles cached
2. Manually note article count
3. Wait for source to publish new content (or mock by clearing one URL from cache)
4. Scrape today again — new articles appear, existing articles retain their state
5. Scrape a past date — cache-first behavior unchanged (no server call if cached)
