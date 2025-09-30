# Cache Mode System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Web UI                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Cache Mode Selector (dropdown)                      │   │
│  │  - Read & Write (Normal)                             │   │
│  │  - Read Only                                         │   │
│  │  - Write Only                                        │   │
│  │  - Disabled                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                 │
│                    API Endpoints                            │
│  GET  /api/cache-mode  →  Returns current mode             │
│  POST /api/cache-mode  →  Sets new mode                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   cache_mode.py (Core)                      │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │  Thread-Safe State Management                       │   │
│  │  - RLock for thread safety                          │   │
│  │  - In-memory cache for performance                  │   │
│  │  - Blob storage for persistence                     │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
│  Public API:                                                │
│  • get_cache_mode() → CacheMode                            │
│  • set_cache_mode(mode) → bool                             │
│  • can_read() → bool                                       │
│  • can_write() → bool                                      │
│  • invalidate_mode_cache()                                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
          ┌────────────────┴────────────────┐
          ↓                                  ↓
┌──────────────────────┐          ┌──────────────────────┐
│  Cache Mechanisms    │          │  Cache Mechanisms    │
│  (Read Operations)   │          │  (Write Operations)  │
├──────────────────────┤          ├──────────────────────┤
│                      │          │                      │
│  if can_read():      │          │  if can_write():     │
│    try blob read ──┐ │          │    write to blob ──┐ │
│    return cached   │ │          │    log success     │ │
│  else:             │ │          │  else:             │ │
│    skip cache ─────┼─┤          │    skip write ─────┼─┤
│                    │ │          │                    │ │
│  execute function  │ │          │  return result     │ │
│  return result     │ │          │                    │ │
└────────────────────┼─┘          └────────────────────┼─┘
                     │                                 │
                     ↓                                 ↓
          ┌──────────────────────────────────────────────┐
          │         Blob Storage (Vercel Blob)           │
          │                                              │
          │  • cache-mode.txt  (mode state)              │
          │  • newsletter-*.json  (newsletter cache)     │
          │  • scrape-day-*.json  (day cache)            │
          │  • *-summary.md  (summaries)                 │
          │  • *.md  (article content)                   │
          └──────────────────────────────────────────────┘
```

## Cache Mode States

### Read & Write (read_write) - Default
```
Request → can_read()=true → Try cache → Hit? Return cached
                                       → Miss? Execute function
                                              → can_write()=true
                                              → Write to cache
                                              → Return result
```

### Read Only (read_only)
```
Request → can_read()=true → Try cache → Hit? Return cached
                                       → Miss? Execute function
                                              → can_write()=false
                                              → Skip cache write
                                              → Return result
```

### Write Only (write_only)
```
Request → can_read()=false → Skip cache read
                            → Execute function
                            → can_write()=true
                            → Write to cache
                            → Return result
```

### Disabled (disabled)
```
Request → can_read()=false → Skip cache read
                            → Execute function
                            → can_write()=false
                            → Skip cache write
                            → Return result
```

## Integration Points

### 1. blob_cache.py
- **blob_cached()** decorator
  - Checks `can_read()` before cache lookup
  - Checks `can_write()` before cache storage
  
- **blob_cached_json()** decorator
  - Checks `can_read()` before cache lookup
  - Checks `can_write()` before cache storage

### 2. blob_newsletter_cache.py
- **get_cached_json()**
  - Early return if `not can_read()`
  
- **put_cached_json()**
  - Early return if `not can_write()`

### 3. serve.py
- **_get_cached_day()**
  - Early return if `not can_read()`
  
- **_put_cached_day()**
  - Early return if `not can_write()`

## Data Flow Example

### Example: Scraping newsletters with different modes

#### Mode: read_write (normal)
```
1. User clicks "Scrape"
2. serve.py checks day cache
   → _get_cached_day() → can_read()=true → Try blob → Cache hit!
3. Returns cached data
4. Stats show: cache_mode=read_write, day_cache_hits=1
```

#### Mode: write_only (rebuild cache)
```
1. User sets mode to write_only
2. User clicks "Scrape"
3. serve.py checks day cache
   → _get_cached_day() → can_read()=false → Skip cache
4. Fetches fresh from TLDR
5. _put_cached_day() → can_write()=true → Writes new cache
6. Stats show: cache_mode=write_only, day_cache_misses=1
```

#### Mode: disabled (no cache)
```
1. User sets mode to disabled
2. User clicks "Scrape"
3. serve.py checks day cache
   → _get_cached_day() → can_read()=false → Skip cache
4. Fetches fresh from TLDR
5. _put_cached_day() → can_write()=false → Skip write
6. Stats show: cache_mode=disabled, day_cache_misses=1
```

## Thread Safety Implementation

```python
# In cache_mode.py
_lock = threading.RLock()  # Reentrant lock
_cached_mode = None        # In-memory cache

def get_cache_mode():
    with _lock:  # Thread-safe
        if _cached_mode:
            return _cached_mode
        # Read from blob storage
        # Update _cached_mode
        return _cached_mode

def set_cache_mode(mode):
    with _lock:  # Thread-safe
        # Write to blob storage first
        # Update _cached_mode
        return success
```

## Web Server Instance Safety

```
Instance 1                    Blob Storage                Instance 2
─────────                    ─────────────               ─────────
set_cache_mode("read_only")
     │
     ├─→ Write to blob ────→ [cache-mode.txt]
     │                           │
     └─→ Update local cache      │
                                 │
                                 │            get_cache_mode()
                                 │                    │
                                 │                    ├─→ Check local cache (miss)
                                 │                    │
                                 └────────────────────┘
                                 Read from blob ←─────┤
                                                      │
                                                      └─→ Update local cache
                                                          Return "read_only"
```

## API Contract

### GET /api/cache-mode
**Response:**
```json
{
  "success": true,
  "cache_mode": "read_write"
}
```

### POST /api/cache-mode
**Request:**
```json
{
  "cache_mode": "read_only"
}
```

**Response (Success):**
```json
{
  "success": true,
  "cache_mode": "read_only"
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Invalid cache_mode. Valid values: disabled, read_only, write_only, read_write"
}
```

## Stats Output

Stats now include cache mode:
```javascript
{
  "success": true,
  "output": "...",
  "stats": {
    "total_articles": 42,
    "unique_urls": 40,
    "dates_processed": 7,
    "dates_with_content": 6,
    "cache_hits": 15,
    "cache_misses": 3,
    "cache_other": 2,
    "blob_cache_hits": 8,
    "blob_cache_misses": 2,
    "blob_store_present": true,
    "cache_mode": "read_write",  // ← NEW
    "debug_logs": [...]
  }
}
```

## Error Handling

1. **Invalid Mode Value**
   - API returns 400 with error message
   - UI shows alert with error
   - Reverts to previous value

2. **Blob Storage Unavailable**
   - Defaults to `read_write` mode
   - Logs warning
   - Continues operation

3. **Mode File Corrupted**
   - Defaults to `read_write` mode
   - Logs warning
   - Overwrites on next set

## Testing Strategy

### Unit Tests (Conceptual)
```python
def test_cache_mode_read_write():
    cache_mode.set_cache_mode(CacheMode.READ_WRITE)
    assert cache_mode.can_read() == True
    assert cache_mode.can_write() == True

def test_cache_mode_read_only():
    cache_mode.set_cache_mode(CacheMode.READ_ONLY)
    assert cache_mode.can_read() == True
    assert cache_mode.can_write() == False

def test_cache_mode_write_only():
    cache_mode.set_cache_mode(CacheMode.WRITE_ONLY)
    assert cache_mode.can_read() == False
    assert cache_mode.can_write() == True

def test_cache_mode_disabled():
    cache_mode.set_cache_mode(CacheMode.DISABLED)
    assert cache_mode.can_read() == False
    assert cache_mode.can_write() == False
```

### Integration Tests
1. Set mode via API → Verify cache behavior
2. Set mode in UI → Scrape → Check stats
3. Multi-instance: Set mode in instance A → Verify in instance B
4. Restart server → Verify mode persists

## Performance Considerations

1. **In-Memory Caching**: Reduces blob reads to ~1 per mode change
2. **Early Returns**: Minimal overhead (2 function calls)
3. **No Polling**: Mode changes propagate on next cache operation
4. **Thread-Safe**: RLock has minimal contention (mode changes are rare)

## Migration Notes

**No breaking changes:**
- Default mode is `read_write` (existing behavior)
- Old code continues to work
- Cache invalidation endpoint still exists (not removed, just UI button removed)
- All existing cache files remain valid