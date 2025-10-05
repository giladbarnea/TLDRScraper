# Cache System Documentation

## Overview

This document covers two major cache optimizations:
1. **Cache Mode System** - Configurable cache behavior (read/write controls)
2. **Architecture Optimization** - Removed redundant newsletter-level cache layer

## Cache Mode System

### Modes

1. **Read & Write (Normal)** - `read_write`
   - Default behavior, reads from cache, writes on miss
   - Use for: Normal operation

2. **Read Only** - `read_only`
   - Only reads from cache, never writes
   - Use for: Testing with existing cache, preventing cache pollution

3. **Write Only** - `write_only`
   - Never reads from cache, always writes
   - Use for: Forcing cache rebuild, updating stale cache

4. **Disabled** - `disabled`
   - No cache reads or writes
   - Use for: Testing without cache, debugging cache issues

### Implementation

**Core Module**: `cache_mode.py`
- Thread-safe using `threading.RLock()`
- In-memory cache with blob storage persistence
- Simple API: `can_read()` and `can_write()`

**Early Return Pattern**: Each cache function checks `can_read()` before cache reads and `can_write()` before cache writes.

### API Endpoints

**GET /api/cache-mode**
```json
{
  "success": true,
  "cache_mode": "read_write"
}
```

**POST /api/cache-mode**
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

### Usage Examples

```bash
# Get current mode
curl http://localhost:5001/api/cache-mode

# Set to read-only mode
curl -X POST http://localhost:5001/api/cache-mode \
  -H "Content-Type: application/json" \
  -d '{"cache_mode": "read_only"}'

# Set to write-only mode (rebuild cache)
curl -X POST http://localhost:5001/api/cache-mode \
  -H "Content-Type: application/json" \
  -d '{"cache_mode": "write_only"}'

# Disable caching
curl -X POST http://localhost:5001/api/cache-mode \
  -H "Content-Type: application/json" \
  -d '{"cache_mode": "disabled"}'
```

### UI Changes

- **Removed**: "Clear Cache for These Dates" button
- **Added**: Cache Mode selector dropdown with descriptive text
- **Added**: Summary Loading Feature - automatically loads summaries for first 10 URLs after scraping (staggered 250ms)
- **Added**: Cache mode display in stats: `⚙️ Cache Mode: **read_write**`

### Stats Output

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
    "cache_mode": "read_write",
    "debug_logs": [...]
  }
}
```


### Cleanup Recommendations

**Optional: Delete Old Newsletter Caches**
```bash
# In blob storage, delete files matching:
newsletter-tech-*.json
newsletter-ai-*.json

# Keep files matching:
scrape-day-*.json  # The single source of truth
```

