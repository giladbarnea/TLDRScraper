---
last_updated: 2026-02-20 13:24, 99f0acd
---
# Backend Storage Layer & Supabase Integration Analysis

## Overview

The storage layer uses Supabase PostgreSQL with two tables (`settings` and `daily_cache`) to persist all application data server-side. Storage is accessed through `storage_service.py` which provides a clean abstraction layer over `supabase_client.py`. Article-level data (including summaries) is stored as JSONB payloads in `daily_cache`, keyed by date.

## Entry Points

1. `storage_service.py` - High-level storage abstraction layer
2. `supabase_client.py` - Singleton Supabase client factory
3. `serve.py:114-219` - REST API endpoints for storage operations
4. `newsletter_merger.py` - Batch article processing patterns

## Core Implementation

### 1. Supabase Client (`supabase_client.py:17-23`)

**Singleton pattern for Supabase connection:**
- Creates client lazily on first access
- Reads `SUPABASE_URL` and `SUPABASE_SECRET_KEY` from environment via `util.resolve_env_var`
- Returns cached `_supabase_client` instance
- SSL verification disabled (lines 5-13) for development/compatibility

### 2. Settings Table CRUD (`storage_service.py:3-30`)

**Pattern: Key-value store for UI preferences and configuration**

#### `get_setting(key)` (`storage_service.py:3-15`)
- Direct SELECT query filtered by key
- Returns `value` field (JSONB type) or `None` if not found
- Example: `get_setting('ui:theme')` → `'dark'`

#### `set_setting(key, value)` (`storage_service.py:17-30`)
- Upsert pattern using `.upsert()` method
- Creates new row or updates existing by primary key
- No timestamp management (table has `updated_at` with DEFAULT NOW())
- Returns full row data or `None`

**Key patterns observed:**
- `ui:*` - UI preferences (e.g., `ui:theme`)
- Settings are simple key-value pairs, not nested structures

### 3. Daily Cache Table CRUD (`storage_service.py:32-115`)

**Pattern: Date-keyed JSONB payloads containing articles and issues**

#### `get_daily_payload(date)` (`storage_service.py:32-44`)
- Returns full payload JSONB for a specific date
- Returns `None` if date not found
- Payload structure: `{date, articles: [...], issues: [...]}`

#### `set_daily_payload(date, payload)` (`storage_service.py:46-62`)
- User-state update path (read/removed/summary changes)
- **Does NOT update `cached_at`** - critical contract
- `cached_at` tracks scrape freshness only, not user interactions
- Used when article state changes (mark read, add summary, remove article)

#### `set_daily_payload_from_scrape(date, payload)` (`storage_service.py:64-80`)
- Scrape operation path
- **Updates `cached_at` to current UTC timestamp**
- Distinguishes fresh scrape data from stale cache
- Returns row with updated `cached_at`

#### `get_daily_payloads_range(start_date, end_date)` (`storage_service.py:82-103`)
- Batch read for date range (inclusive)
- Returns array of `{date, payload, cached_at}` objects
- Ordered by date descending
- Powers multi-day views in the frontend

#### `is_date_cached(date)` (`storage_service.py:105-115`)
- Simple existence check
- Returns boolean
- Used to determine cache-first vs scrape-first strategy

### 4. REST API Endpoints (`serve.py:114-219`)

**Storage routes follow RESTful patterns:**

- `GET /api/storage/setting/<key>` → `get_setting(key)`
- `POST /api/storage/setting/<key>` → `set_setting(key, value)`
- `GET /api/storage/daily/<date>` → `get_daily_payload(date)`
- `POST /api/storage/daily/<date>` → `set_daily_payload(date, payload)`
- `POST /api/storage/daily-range` → `get_daily_payloads_range(start, end)`
- `GET /api/storage/is-cached/<date>` → `is_date_cached(date)`

**Response format:**
```python
{"success": True, "payload": {...}}  # or "value", "data", "is_cached"
{"success": False, "error": "..."}
```

### 5. Batch Article Processing (`newsletter_merger.py`)

**Purpose:** Format multiple articles into unified markdown output

#### `build_markdown_output()` (`newsletter_merger.py:15-168`)
- Takes grouped articles by date and issue metadata
- Generates neutral markdown (no TLDR branding)
- Groups by: date → category → section
- Respects source `sort_order` from `NEWSLETTER_CONFIGS`
- Handles section hierarchy with emoji support
- Marks removed articles with `?data-removed=true` URL param

**Key patterns:**
- Articles grouped by `date` → `category` → `section_order`
- Issue metadata indexed by `(date, source_id, category)` tuple
- Sections have `{order, title, emoji}` structure
- Remaining articles (no section assignment) appended last

## Data Flow

### Article Summary Storage Flow

1. **User requests summary**: `POST /api/summarize-url` (`serve.py:78`)
2. **Summary generated**: `tldr_app.summarize_url()` → `summarizer.py:tldr_url()`
3. **Result format**: `{"success": True, "summary_markdown": "..."}`
4. **Client updates article**: `useSummary.js:123-128` dispatches `SUMMARY_LOAD_SUCCEEDED`
5. **State persisted**: `useArticleState` → `POST /api/storage/daily/{date}` → `set_daily_payload()`
6. **JSONB structure**: Article object gains `summary` or `tldr` field with nested object

### Cache vs Scrape Timestamp Contract

```
set_daily_payload_from_scrape()
  ↓
  Updates cached_at = NOW()
  ↓
  Signals fresh scrape data

set_daily_payload()
  ↓
  Preserves existing cached_at
  ↓
  User state changes only
```

## Daily Cache Table Structure

```sql
CREATE TABLE daily_cache (
  date DATE PRIMARY KEY,
  payload JSONB NOT NULL,
  cached_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Payload JSONB schema:**
```typescript
{
  date: string,              // "2024-01-01"
  articles: Article[],       // Array of article objects
  issues: Issue[]            // Array of newsletter issue metadata
}
```

**Article structure (from test files):**
```javascript
{
  url: string,               // Canonical URL (unique ID)
  title: string,
  articleMeta: string,       // Source-specific metadata
  issueDate: string,         // "2024-01-01"
  category: string,          // "TLDR Tech", "HackerNews"
  sourceId: string | null,
  section: string | null,
  sectionEmoji: string | null,
  sectionOrder: number | null,
  newsletterType: string | null,
  removed: boolean,

  // User state (stored per article in payload)
  tldr: {                    // Summary data
    status: "unknown" | "loading" | "available" | "error",
    markdown: string,
    effort: "low" | "medium" | "high",
    checkedAt: string | null,  // ISO timestamp
    errorMessage: string | null
  },

  read: {                    // Read state
    isRead: boolean,
    markedAt: string | null    // ISO timestamp
  }
}
```

**Issue structure:**
```javascript
{
  date: string,              // "2024-01-01"
  source_id: string,         // "tldr_tech"
  category: string,          // "TLDR Tech"
  title: string | null,
  subtitle: string | null,
  sections: [                // Section hierarchy
    {
      order: number,
      title: string,
      emoji: string
    }
  ]
}
```

## Settings Table Structure

```sql
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Key patterns:**
- `ui:*` - UI preferences (e.g., `ui:theme`)
- Simple key-value, no nesting observed in current usage

## Configuration

- Environment: `SUPABASE_URL`, `SUPABASE_SECRET_KEY` (via `util.resolve_env_var`)
- Connection: Singleton client with SSL verification disabled
- Tables: `settings`, `daily_cache`
- All operations use `.execute()` and return `.data` array

## Error Handling

- Storage service functions return `None` on not-found (no exceptions)
- REST endpoints catch all exceptions and return 500 with error message
- Logging via `logger.error()` with `exc_info=True` for full tracebacks
- Client receives `{"success": False, "error": "..."}` on failure

## Digest Storage Decision Guidance

### Option A: Embed in `daily_cache` payloads

**Pattern:** Add `digest` field to existing payload structure
```javascript
{
  date: "2024-01-01",
  articles: [...],
  issues: [...],
  digest: {                  // NEW: Article digest
    status: "unknown" | "loading" | "available" | "error",
    markdown: string,
    generatedAt: string,
    articleUrls: string[],   // URLs included in digest
    errorMessage: string | null
  }
}
```

**Pros:**
- Follows existing pattern (summaries are embedded in articles)
- No schema changes needed (JSONB is flexible)
- Leverages existing `set_daily_payload()` / `get_daily_payload()` functions
- Natural association: digest lives with the articles it summarizes
- Cache invalidation automatic (digest saved with payload)

**Cons:**
- Payload size grows (but JSONB handles this well)
- One digest per date (no multi-date digests without new approach)

### Option B: Store in `settings` table

**Pattern:** Key like `digest:{date}` or `digest:weekly:{week_id}`
```javascript
// settings table row
{
  key: "digest:2024-01-01",
  value: {
    status: "available",
    markdown: "...",
    generatedAt: "...",
    articleUrls: [...]
  }
}
```

**Pros:**
- Separates digest lifecycle from article cache
- Can create arbitrary digest keys (daily, weekly, custom ranges)
- Simple CRUD via existing `get_setting()` / `set_setting()`

**Cons:**
- Settings table not semantically correct (digests aren't settings)
- No date-range queries (can't efficiently fetch all digests for a month)
- Key pattern pollution

### Option C: New `digests` table

**Pattern:** Dedicated table with proper schema
```sql
CREATE TABLE digests (
  id SERIAL PRIMARY KEY,
  date_start DATE NOT NULL,
  date_end DATE NOT NULL,
  digest JSONB NOT NULL,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(date_start, date_end)
);
```

**Pros:**
- Proper semantic modeling
- Supports multi-day digests naturally
- Can add metadata (user_id, digest_type, etc.) later
- Efficient date-range queries

**Cons:**
- Requires schema migration in Supabase
- New CRUD functions in `storage_service.py`
- New REST endpoints in `serve.py`
- More upfront complexity

## Recommendation

**Start with Option A (embed in `daily_cache`)** for MVP:

1. **Reasoning:**
   - Digests are derived content from articles, similar to summaries
   - Daily digests map 1:1 with daily payloads
   - Zero schema changes, zero new endpoints
   - Can migrate to Option C later if multi-day or complex digests needed

2. **Implementation path:**
   - Add optional `digest` field to payload JSONB
   - Client hook `useDigest(date)` mirrors `useSummary(date, url)` pattern
   - Store digest via existing `POST /api/storage/daily/{date}`
   - Digest status follows same state machine as summary (unknown → loading → available/error)

3. **When to migrate to Option C:**
   - Need multi-day digests (weekly, monthly)
   - Need digest history/versioning
   - Need user-specific digests
   - Payload size becomes problematic (unlikely with markdown digests)

**Existing pattern to follow:** The `summary`/`tldr` field on articles shows exactly how to embed derived content in payloads. Digests should follow the same pattern at the payload level.
