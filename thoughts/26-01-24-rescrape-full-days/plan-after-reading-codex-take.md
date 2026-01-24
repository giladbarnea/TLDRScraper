---
last_updated: 2026-01-24 14:41, ef482d1
---
# Plan After Reading Codex Take

## Codex Analysis Summary

Codex successfully ran and provided substantive analysis. Key points:

**What Codex found:**
- The "today vs not-today" special-case is entirely in `tldr_service.py` (lines 162, 195, 221)
- `daily_cache.cached_at` column exists but is **never updated on rescrapes** - `set_daily_payload()` only upserts `{date, payload}`, leaving `cached_at` at its insert-time value
- This means if we use `cached_at` for freshness without fixing the write, days will look "stale forever" and keep rescraping

**Codex's recommended approach:**
1. Keep `last_scraped_at` out of JSON payload, use the database `cached_at` column
2. **Add new functions** rather than modifying existing ones:
   - Add `get_daily_cache_rows_range()` that returns `{date, payload, cached_at}`
   - Add `set_daily_payload_from_scrape()` that explicitly sets `cached_at=now()`
   - Leave `get_daily_payload()` / `get_daily_payloads_range()` unchanged to avoid breaking `serve.py:150` and `serve.py:190`
3. Replace today-branch with unified stale vs fresh check
4. Reuse existing merge + `cached_urls` exclusion logic for rescrapes

---

## My Assessment of Codex's Points

### Valid Point: `cached_at` Not Updated on Writes

Codex correctly identified a critical gotcha I also noted: the current `set_daily_payload()` doesn't update `cached_at` on upserts. This must be fixed.

### Difference in Approach: New Functions vs. Modified Functions

| Aspect | My Plan | Codex's Plan |
|--------|---------|--------------|
| Read functions | Modify `get_daily_payloads_range()` to return `{date, payload, cached_at}` | Add new `get_daily_cache_rows_range()` |
| Write functions | Modify `set_daily_payload()` to set `cached_at=now()` | Add new `set_daily_payload_from_scrape()` |
| Impact on `serve.py` | Requires updating `serve.py:194` | No changes to `serve.py` |
| Code complexity | Fewer functions, but breaking change | More functions, but safer |

**My verdict on this difference:**

Codex's concern about breaking `serve.py` is valid but overstated. Looking at the code:
- `serve.py:194` uses `get_daily_payloads_range()` for the `/api/storage/daily` endpoint
- This endpoint returns raw payloads to the client
- If we change the return format to `[{date, payload, cached_at}, ...]`, we'd need to extract just the payload before returning

However, I prefer **my original approach** because:
1. It's simpler - one function to maintain, not two
2. The `serve.py` change is trivial: `[row['payload'] for row in payloads]`
3. Having both `get_daily_payloads_range()` and `get_daily_cache_rows_range()` is confusing
4. The principle of "don't add abstractions unless clearly necessary" applies

For the write side, Codex raises a valid distinction:
- `/api/scrape` should update `cached_at` (it's a scrape)
- `/api/storage/daily/<date>` (user state changes) should NOT update `cached_at`

This means we **do** need two write paths. Options:
1. Add parameter: `set_daily_payload(date, payload, update_cached_at=False)`
2. Add new function: `set_daily_payload_from_scrape(date, payload)`

I'll go with option 2 (new function) because:
- It's explicit - the function name documents intent
- No risk of accidentally passing wrong parameter
- Follows single responsibility principle

---

## Final Plan (After Codex Input)

### Changes from original plan:

1. **Keep `get_daily_payloads_range()` modification** - change return type, update `serve.py:194` accordingly
2. **Add `set_daily_payload_from_scrape()`** instead of modifying existing write function
3. Keep everything else the same

### Files to modify:

| File | Changes |
|------|---------|
| `storage_service.py` | Modify `get_daily_payloads_range()` to return `[{date, payload, cached_at}]`; Add `set_daily_payload_from_scrape()` that upserts with `cached_at=now()` |
| `util.py` | Add `should_rescrape(date_str, cached_at_iso)` function |
| `tldr_service.py` | Replace "today vs not-today" with `should_rescrape()` calls; Use `set_daily_payload_from_scrape()` |
| `serve.py` | Update `/api/storage/daily` range endpoint to extract payloads from new format |
| `tests/test_scrape_cache_server.py` | Update mocks for new return format, add `cached_at` to test fixtures |

### What Codex got right:
- The `cached_at` update issue - critical catch
- Need for separate write paths for scrape vs user state changes
- Using `cached_at` column rather than embedding timestamp in payload

### Where I diverge from Codex:
- I'll modify the existing read function rather than adding a parallel one
- This keeps the codebase simpler at the cost of one trivial change in `serve.py`

---

## Ready to Implement

The plan is solid. Both Codex and I converged on the core approach:
- Use `cached_at` for freshness
- Unified stale/fresh check replacing today special case
- Preserve merge semantics for rescrapes

The differences are implementation details, not architectural. Proceeding with implementation.
