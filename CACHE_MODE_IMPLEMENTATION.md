# Cache Mode Implementation

## Overview

This implementation adds a configurable cache mode system that allows users to control caching behavior across the entire application. The clear cache button has been removed and replaced with a cache mode selector offering four states.

## Cache Modes

1. **Read & Write (Normal)** - `read_write`
   - Default behavior
   - Reads from cache on requests
   - Writes to cache on cache miss
   - Use for: Normal operation

2. **Read Only** - `read_only`
   - Only reads from cache
   - Never writes to cache
   - Use for: Testing with existing cache, preventing cache pollution

3. **Write Only** - `write_only`
   - Never reads from cache (always fetches fresh data)
   - Always writes to cache (rebuilding cache)
   - Use for: Forcing cache rebuild, updating stale cache

4. **Disabled** - `disabled`
   - No cache reads
   - No cache writes
   - Use for: Testing without cache, debugging cache issues

## Implementation Details

### Architecture

The implementation follows a **transparent, early-return pattern** that affects all caching mechanisms:

1. **Core Module**: `cache_mode.py`
   - Thread-safe using `threading.RLock()`
   - Web-server-instance-safe via blob storage
   - In-memory caching with blob storage persistence
   - Simple API: `can_read()` and `can_write()`

2. **Cache Integration Points**:
   - `blob_cache.py` - Decorators for text and JSON caching
   - `blob_newsletter_cache.py` - Newsletter-specific cache
   - `serve.py` - Day-level scrape cache

3. **Early Return Pattern**:
   - Each cache function checks `can_read()` before attempting cache reads
   - Each cache function checks `can_write()` before attempting cache writes
   - No changes required to business logic
   - Transparent to calling code

### Thread Safety

- Uses `threading.RLock()` for thread-safe mode access
- In-memory cache prevents excessive blob reads
- Atomic read-modify-write for mode changes

### Web Server Instance Safety

- Cache mode stored in blob storage (`cache-mode.txt`)
- All instances read from the same blob storage
- Mode changes propagate to all instances on next read
- Optional `invalidate_mode_cache()` to force immediate reload

### API Endpoints

1. **GET /api/cache-mode**
   - Returns current cache mode
   - Response: `{"success": true, "cache_mode": "read_write"}`

2. **POST /api/cache-mode**
   - Sets cache mode
   - Request: `{"cache_mode": "read_only"}`
   - Response: `{"success": true, "cache_mode": "read_only"}`

### UI Changes

1. **Removed**: "Clear Cache for These Dates" button
2. **Added**: Cache Mode selector dropdown
   - Shows current mode on page load
   - Updates immediately on change
   - Displays descriptive text for each mode
   - Shows success confirmation after mode change

3. **Added**: Summary Loading Feature
   - Automatically loads summaries for first 10 URLs after scraping
   - Staggered requests (250ms delay) to avoid overwhelming the server
   - Visual indicators: buttons turn green when summary is loaded
   - Instant display when user clicks expand (no waiting)
   - Uses `cache_only=true` parameter to only fetch from blob store (no LLM calls)
   - Client-side storage in `data-summary` attribute for instant access

4. **Stats Display**:
   - Cache mode now appears in stats block after scraping
   - Format: `⚙️ Cache Mode: **read_write**`
   - Updates automatically after scrape completion

## Files Modified

1. **New Files**:
   - `cache_mode.py` - Core cache mode management

2. **Modified Files**:
   - `blob_cache.py` - Added mode checks to decorators, added `cache_only` parameter support
   - `blob_newsletter_cache.py` - Added mode checks to get/put functions
   - `serve.py` - Added mode checks to day cache, added API endpoints, added mode to stats, added `cache_only` parameter to `/api/summarize-url`
   - `summarizer.py` - Added `cache_only` parameter support to `summarize_url()`
   - `templates/index.html` - Removed clear cache button, added mode selector, updated stats display, added summary loading with visual indicators

## Summary Loading Feature

### Overview
After scraping newsletters, the UI automatically loads summaries for the first 10 URLs in the background. This provides instant access to summaries without waiting for LLM calls.

### How It Works
1. **Trigger**: Automatically runs after successful scrape completion
2. **Scope**: First 10 URLs only (to avoid overwhelming server)
3. **Method**: Staggered requests with 250ms delay between each
4. **Efficiency**: Uses `cache_only=true` to only fetch from blob store (no LLM calls)
5. **Visual Feedback**: Buttons turn green when summary is loaded
6. **Client Storage**: Summaries stored in `data-summary` attribute for instant display

### User Experience
- **Before loading**: Expand button shows default state
- **After loading**: Button turns green (indicates summary is ready)
- **On click**: Summary displays instantly (no network request needed)
- **On click (not loaded)**: Fetches summary normally (may call LLM if not cached)

### Technical Details
```javascript
// Function: loadSummaries()
// - Queries first 10 .expand-btn elements
// - Sends POST to /api/summarize-url with cache_only=true
// - On success: Adds 'loaded' class and stores summary in data-summary
// - On failure: Silently ignores (user can still fetch manually)
```

### Backend Support
- `blob_cache.py`: `cache_only` parameter returns `None` on cache miss instead of calling function
- `summarizer.py`: Passes `cache_only` through to decorated function
- `serve.py`: Returns `success: false` when `cache_only=true` and no cache available

### CSS Styling
```css
.article-btn.expand-btn.loaded {
  background: #e8f5e9;      /* Light green background */
  border-color: #4caf50;    /* Green border */
  color: #2e7d32;           /* Dark green text */
}
```

## Usage Examples

### Via UI
1. Open the web interface
2. Select desired cache mode from dropdown
3. Mode is applied immediately to all subsequent operations
4. Scrape newsletters to see mode in action
5. Check stats block to confirm current mode
6. Notice first 10 URLs turn green as summaries load in background

### Via API
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

# Return to normal
curl -X POST http://localhost:5001/api/cache-mode \
  -H "Content-Type: application/json" \
  -d '{"cache_mode": "read_write"}'
```

## Design Principles

1. **Stupid Simple**: Two functions (`can_read()`, `can_write()`), early returns
2. **Transparent**: Business logic unchanged, all changes in cache layer
3. **Thread-Safe**: RLock protects shared state
4. **Instance-Safe**: Blob storage provides cross-instance coordination
5. **Early Return**: Clean, readable code with minimal nesting
6. **No Breaking Changes**: Default mode is `read_write` (normal behavior)

## Testing Recommendations

1. **Read-Only Mode**:
   - Set mode to read-only
   - Scrape with existing cache - should use cache
   - Delete a cache file and scrape again - should fail to fetch that day

2. **Write-Only Mode**:
   - Set mode to write-only
   - Scrape - should always fetch fresh data
   - Check blob storage - should see updated cache files
   - Set back to read_write and scrape - should use newly rebuilt cache

3. **Disabled Mode**:
   - Set mode to disabled
   - Scrape - should always fetch fresh, never write
   - Check blob storage - no new cache files

4. **Multi-Instance**:
   - Run two server instances
   - Change mode in one instance
   - Wait a few seconds (for in-memory cache to expire if needed)
   - Make request in second instance
   - Should reflect the mode change

## Notes

- Default mode is `read_write` if not set or on error
- Cache mode persists across server restarts (stored in blob)
- In-memory cache reduces blob reads for performance
- All cache mechanisms respect the mode uniformly
- Mode changes take effect immediately for new requests

