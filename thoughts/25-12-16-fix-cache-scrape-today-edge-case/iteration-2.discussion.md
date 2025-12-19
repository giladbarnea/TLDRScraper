---
last_updated: 2025-12-19 18:22
---
# Iteration 2: Discussion — Incomplete Cache & Failed Source Tracking

## Problem Statement

When a scrape partially fails (some sources succeed, others fail), the failure information is lost. Successful results are cached, and on re-scrape, cache-first logic uses the incomplete cache. Failed sources are never retried.

Example: TLDR.tech times out on Dec 18's scrape, but HN succeeds. The HN articles are cached. On the next scrape of Dec 18, cache-first logic sees the payload exists and returns it. TLDR.tech articles are permanently missing from that date.

---

## Current Situation (Post Iteration-1)

### How cache-first works now

The server iterates through each date in the requested range:

```
for date in range:
    if date == today:
        → union logic (always scrapes, merges with cache)
    else:
        cached = storage_service.get_daily_payload(date)
        if cached:
            → use cached data, skip scraping
        else:
            → scrape
```

The cache existence check is binary: payload exists or it doesn't. There is no notion of "complete" vs "incomplete" cache.

### How errors are handled now

In `newsletter_scraper.py`, per-source scraping is wrapped in try/except:

```python
try:
    adapter = _get_adapter_for_source(config)
    result = adapter.scrape_date(date, excluded_urls)
    # process articles...
except Exception as e:
    logger.error(f"Error processing {config.display_name} for {date_str}: {e}")
    # continues to next source
```

Failures are logged and swallowed. The scrape continues with whatever sources succeeded. No failure information is persisted.

### How `cachedAt` works now

`cachedAt` is a timestamp set by the **client** when building payloads from the server's response:

```javascript
// client/src/lib/scraper.js
payloads.push({
  date,
  cachedAt: new Date().toISOString(),  // ← client sets this
  articles,
  issues
})
```

The client then persists this to Supabase via `storageApi.setDailyPayload()`.

The server has no visibility into when or whether data was cached. It reads from the same `daily_cache` table but treats payload existence as the only signal.

---

## Why This Binds Us to the Problem

1. **No per-source tracking**: We know a date has cached data, but not which sources contributed to it. If 3 of 20 sources failed, we have no record.

2. **No failure persistence**: Errors are logged to stdout/stderr and vanish. Nothing in the database indicates "TLDR.tech failed for Dec 18."

3. **Binary cache check**: `get_daily_payload(date)` returns the payload or None. There's no metadata about completeness.

4. **Retry is impossible**: Without knowing which sources failed, we can't selectively retry them. The only option would be to clear the entire day's cache and re-scrape everything.

---

## Architectural Concern: Cache Ownership

Cache persistence is currently in the client's domain. The client decides when to write `cachedAt`, how to structure the payload, and when to persist.

This is problematic:
- The **server** knows scrape outcomes (which sources succeeded, which failed, what errors occurred)
- The **client** has no visibility into partial failures — it just receives whatever the server returned
- Cache integrity is a server-side concern; the client is a consumer

Regardless of what design we pick for tracking failures, **cache persistence should move to the server's domain**.

---

## Open Questions for Next Session

These need resolution before designing a solution:

1. **What constitutes a "complete" cache entry?**
   - All configured sources succeeded?
   - All sources that had content for that date succeeded?
   - How do we distinguish "source had nothing to publish" from "source failed"?

2. **Error classification**
   - Which errors are retriable? (timeout, 5xx, rate limit)
   - Which are permanent? (404, auth failure, malformed response)
   - Should we track error type to inform retry strategy?

3. **Retry policy**
   - Automatic on next scrape of that date?
   - Require explicit user action?
   - Time-based backoff?

4. **Granularity of tracking**
   - Per-date? Per-source-per-date?
   - Store in the payload itself, or separate metadata table?
