## Implementation Plan: Fix Newsletter Cache Logic

### Problem Summary

The current cache logic has a "today vs not today" special case:
- **Today**: Always rescrapes and merges with cache (to catch newly published articles)
- **Any other day**: Uses cache if it exists, never rescrapes

This is flawed because articles published later in any given day are missed if the initial scrape happened earlier that day. The problem exists for all days, not just today.

### Current Implementation Analysis

**Key file: `/home/user/TLDRScraper/tldr_service.py`**

The "today" special case logic is in `scrape_newsletters_in_date_range()`:

1. **Line 162**: Defines today - `today_str = date_type.today().isoformat()`

2. **Lines 179-183**: Fast-path check that skips all dates only if NONE is today AND all are cached:
```python
all_cached_and_not_today = all(
    util.format_date_for_url(d) != today_str and util.format_date_for_url(d) in cache_map
    for d in dates
)
```

3. **Lines 195-219**: TODAY branch - always scrapes even if cached, then merges

4. **Lines 220-232**: NOT-TODAY branch - uses cache if available, else scrapes

**Database schema** (`daily_cache` table):
- `date` (DATE PRIMARY KEY)
- `payload` (JSONB)
- `cached_at` (TIMESTAMPTZ DEFAULT NOW()) - **exists but is never read**

**Key insight**: The `cached_at` column already tracks when cache was written, but it is not retrieved or used in any logic.

---

### New Logic

Replace the binary "today vs not today" check with a time-based check:

```
should_rescrape(date_str, last_scraped_at) =
    last_scraped_at is None
    OR
    last_scraped_at < next_day_midnight_pacific(date_str)
```

Where `next_day_midnight_pacific(date_str)` is:
- Take `date_str` (e.g., "2025-01-23")
- Add 1 day -> "2025-01-24"
- Convert to 00:00:00 AM in America/Los_Angeles timezone
- This represents the latest possible moment an article could be published for that date

**Example**:
- Scraping date "2025-01-23"
- Threshold = 2025-01-24 00:00:00 Pacific = 2025-01-24 08:00:00 UTC
- If `cached_at` = 2025-01-23 15:00:00 UTC (morning scrape) -> rescrape needed
- If `cached_at` = 2025-01-24 09:00:00 UTC (after Pacific midnight) -> use cache

---

### Step-by-Step Implementation

#### Step 1: Modify storage_service.py to return cached_at

**File**: `/home/user/TLDRScraper/storage_service.py`

**Change 1a**: Modify `get_daily_payload()` (lines 32-44)

Current:
```python
def get_daily_payload(date):
    result = supabase.table('daily_cache').select('payload').eq('date', date).execute()
    if result.data:
        return result.data[0]['payload']
    return None
```

New:
```python
def get_daily_payload(date):
    result = supabase.table('daily_cache').select('payload, cached_at').eq('date', date).execute()
    if result.data:
        row = result.data[0]
        return row['payload'], row['cached_at']
    return None, None
```

**Change 1b**: Modify `get_daily_payloads_range()` (lines 61-76)

Current:
```python
def get_daily_payloads_range(start_date, end_date):
    result = supabase.table('daily_cache') \
        .select('payload') \
        ...
    return [row['payload'] for row in result.data]
```

New:
```python
def get_daily_payloads_range(start_date, end_date):
    result = supabase.table('daily_cache') \
        .select('date, payload, cached_at') \
        ...
    return [
        {'date': row['date'], 'payload': row['payload'], 'cached_at': row['cached_at']}
        for row in result.data
    ]
```

---

#### Step 2: Add timezone helper function

**File**: `/home/user/TLDRScraper/util.py`

Add new function (uses Python 3.11+ built-in `zoneinfo`):

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PACIFIC_TZ = ZoneInfo("America/Los_Angeles")

def should_rescrape(date_str: str, cached_at_iso: str | None) -> bool:
    """
    Determine if a date needs rescraping based on when it was last scraped.

    Returns True if cached_at is before the next day's 00:00 AM Pacific time,
    meaning articles could still have been published after the cache was written.

    >>> should_rescrape("2025-01-23", None)
    True
    >>> should_rescrape("2025-01-23", "2025-01-24T09:00:00+00:00")  # after Pacific midnight
    False
    """
    if cached_at_iso is None:
        return True

    # Parse the target date and compute next day midnight Pacific
    target_date = datetime.fromisoformat(date_str)
    next_day = target_date + timedelta(days=1)
    next_day_midnight_pacific = datetime(
        next_day.year, next_day.month, next_day.day,
        0, 0, 0, tzinfo=PACIFIC_TZ
    )

    # Parse cached_at (ISO format with timezone from Supabase)
    cached_at = datetime.fromisoformat(cached_at_iso.replace('Z', '+00:00'))

    return cached_at < next_day_midnight_pacific
```

---

#### Step 3: Update tldr_service.py to use new logic

**File**: `/home/user/TLDRScraper/tldr_service.py`

**Change 3a**: Update imports (line 1-16)

Add:
```python
import util  # already imported
```

**Change 3b**: Update cache map building (lines 174-176)

Current:
```python
all_cached_payloads = storage_service.get_daily_payloads_range(start_date_text, end_date_text)
cache_map: dict[str, dict] = {payload["date"]: payload for payload in all_cached_payloads}
```

New (adapt to new return format):
```python
all_cached_rows = storage_service.get_daily_payloads_range(start_date_text, end_date_text)
cache_map: dict[str, dict] = {}
cached_at_map: dict[str, str | None] = {}
for row in all_cached_rows:
    date_key = row['date']
    cache_map[date_key] = row['payload']
    cached_at_map[date_key] = row['cached_at']
```

**Change 3c**: Replace fast-path check (lines 179-190)

Current:
```python
all_cached_and_not_today = all(
    util.format_date_for_url(d) != today_str and util.format_date_for_url(d) in cache_map
    for d in dates
)
if all_cached_and_not_today:
    ...
```

New:
```python
all_cached_and_fresh = all(
    util.format_date_for_url(d) in cache_map
    and not util.should_rescrape(util.format_date_for_url(d), cached_at_map.get(util.format_date_for_url(d)))
    for d in dates
)
if all_cached_and_fresh:
    ...
```

**Change 3d**: Replace the main loop logic (lines 192-232)

Current has two branches based on `date_str == today_str`. New logic uses uniform `should_rescrape()` check:

```python
for current_date in dates:
    date_str = util.format_date_for_url(current_date)
    cached_payload = cache_map.get(date_str)
    cached_at = cached_at_map.get(date_str)

    if util.should_rescrape(date_str, cached_at):
        # Rescrape needed: either no cache or cache is stale
        cached_urls: set[str] = set()
        if cached_payload:
            for article in cached_payload.get('articles', []):
                url = article.get('url', '')
                canonical_url = util.canonicalize_url(url) if url else ''
                if canonical_url:
                    cached_urls.add(canonical_url)

        combined_excluded = list(set(excluded_urls or []) | cached_urls)
        result = scrape_date_range(current_date, current_date, source_ids, combined_excluded)
        total_network_fetches += result.get('stats', {}).get('network_fetches', 0)

        new_payload = _build_payload_from_scrape(
            date_str,
            result.get('articles', []),
            result.get('issues', []),
        )
        if cached_payload:
            payloads_by_date[date_str] = _merge_payloads(new_payload, cached_payload)
        else:
            payloads_by_date[date_str] = new_payload
        dates_to_write.add(date_str)
    else:
        # Cache is fresh, use it directly
        payloads_by_date[date_str] = cached_payload
```

**Change 3e**: Remove `today_str` variable (line 162)

This variable is no longer needed. Delete:
```python
today_str = date_type.today().isoformat()
```

---

#### Step 4: Update tests

**File**: `/home/user/TLDRScraper/tests/test_scrape_cache_server.py`

**Change 4a**: Update `_stub_storage()` to return cached_at

The mock needs to return the new format from `get_daily_payloads_range`:
```python
def get_daily_payloads_range(start_date, end_date):
    dates = sorted(store.keys(), reverse=True)
    filtered = [
        {'date': date_text, 'payload': store[date_text], 'cached_at': cached_at_store.get(date_text)}
        for date_text in dates if start_date <= date_text <= end_date
    ]
    return filtered
```

And update `get_daily_payload` to return tuple:
```python
def get_daily_payload(date_text):
    if date_text in store:
        return store[date_text], cached_at_store.get(date_text)
    return None, None
```

**Change 4b**: Rename `test_scrape_unions_today_with_cached_state`

This test verifies the merge behavior when rescraping. Rename to reflect the new logic:
```python
def test_scrape_unions_stale_cache_with_new_articles(monkeypatch):
```

And adjust the setup to use a stale `cached_at` value instead of relying on "today".

**Change 4c**: Add new test for fresh cache (no rescrape)

```python
def test_scrape_uses_cache_when_cached_after_pacific_midnight(monkeypatch):
    """If cached_at is after the next day's Pacific midnight, cache is used."""
    ...
```

---

### Files to Modify

| File | Changes |
|------|---------|
| `/home/user/TLDRScraper/util.py` | Add `should_rescrape()` function with timezone logic |
| `/home/user/TLDRScraper/storage_service.py` | Modify `get_daily_payload()` and `get_daily_payloads_range()` to return `cached_at` |
| `/home/user/TLDRScraper/tldr_service.py` | Replace "today vs not today" logic with `should_rescrape()` checks |
| `/home/user/TLDRScraper/tests/test_scrape_cache_server.py` | Update mocks and tests for new logic |

---

### Testing Strategy

1. **Unit test `should_rescrape()`**: Test edge cases around Pacific midnight
2. **Integration test**: Verify server correctly rescrapes stale cache
3. **Integration test**: Verify server uses fresh cache without rescraping
4. **Manual test**: Scrape a date, wait, scrape again before Pacific midnight, verify rescrape occurs

---

### Risks and Mitigations

1. **Risk**: Supabase returns `cached_at` in unexpected format
   - **Mitigation**: Add defensive parsing with `fromisoformat()` and handle 'Z' suffix

2. **Risk**: Timezone logic edge cases (DST transitions)
   - **Mitigation**: Use `ZoneInfo` which handles DST correctly; add tests around DST boundaries

3. **Risk**: Breaking change to `get_daily_payload()` return type
   - **Mitigation**: The only caller is `tldr_service.py` which is being updated simultaneously

---

### Critical Files for Implementation

- `/home/user/TLDRScraper/tldr_service.py` - Core logic with "today" special case to replace (lines 162, 179-232)
- `/home/user/TLDRScraper/storage_service.py` - Database layer to return `cached_at` column
- `/home/user/TLDRScraper/util.py` - Add `should_rescrape()` timezone helper function
- `/home/user/TLDRScraper/tests/test_scrape_cache_server.py` - Tests to update for new behavior
- `/home/user/TLDRScraper/ARCHITECTURE.md` - Reference for database schema (lines 988-1006)
