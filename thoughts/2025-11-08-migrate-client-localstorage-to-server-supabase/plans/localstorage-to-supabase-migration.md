---
last-updated: 2025-11-10 10:40, 48c8242
---
# localStorage to Supabase Database Migration Plan

## Overview

Migrate TLDRScraper's client-side localStorage state machine to server-side Supabase Database (Postgres) while maintaining 1:1 feature parity with current behavior. All user interactions → storage state transitions → DOM updates must work identically, including across page refreshes.

**Migration Strategy**: 1:1 JSONB mapping for simplicity. Store DailyPayloads as JSONB blobs to match current localStorage structure exactly.

## Current State Analysis

### Storage Architecture
- **Client-side only**: All state in browser localStorage
- **Two key patterns**:
  1. `cache:enabled` → boolean (settings)
  2. `newsletters:scrapes:{date}` → DailyPayload with articles array
- **Zero latency**: Synchronous read/write operations
- **State machine**: 4 article states (0=unread, 1=read, 2=tldrHidden, 3=removed) control CSS and sorting

### Key User Flows (Must Preserve)
1. **Mark as read**: Click article → `read.isRead=true` → localStorage → event → re-sort
2. **Remove article**: Click "Remove" → `removed=true` → localStorage → event → re-sort
3. **Generate TLDR**: Click "TLDR" → API → `tldr.markdown` → localStorage
4. **Hide TLDR**: Collapse → `tldrHidden=true` → localStorage → re-sort
5. **Page refresh**: Load from localStorage → restore all states (except UI-only `expanded`)
6. **Scrape**: Check cache → API if needed → merge with existing state → localStorage

### Storage Dependencies Discovered
- **Direct localStorage usage**: 5 locations (useLocalStorage.js:36,101,105,117; scraper.js:55,129,150,154,158,170; ArticleList.jsx:21)
- **Hooks consuming storage**: useArticleState, useSummary, useLocalStorage
- **Components using storage**: CacheToggle, ScrapeForm, ResultsDisplay, ArticleList, ArticleCard, App
- **Event system**: Custom `'local-storage-change'` event triggers ArticleList re-sort

### CSS States Mapped
| State | Storage Fields | CSS Classes | Visual | Sorting Priority |
|-------|---------------|-------------|---------|------------------|
| Unread | `read.isRead=false` | `article-card unread` | Bold blue | 0 (top) |
| Read | `read.isRead=true` | `article-card read` | Muted gray | 1 |
| TLDR Hidden | `tldrHidden=true` | `article-card tldr-hidden` | 60% opacity | 2 |
| Removed | `removed=true` | `article-card removed` | Strikethrough, dashed | 3 (bottom) |

**Critical**: States are additive (can be both `read` AND `tldr-hidden`). Sorting uses numeric priority.

## Desired End State

### Database Schema

```sql
-- Table 1: Daily newsletter cache
CREATE TABLE daily_cache (
  date DATE PRIMARY KEY,
  payload JSONB NOT NULL,
  cached_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 2: Application settings
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS (service_role key bypasses RLS)
ALTER TABLE daily_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
```

**Payload JSONB Structure** (matches localStorage exactly):
```json
{
  "date": "2025-11-09",
  "cachedAt": "2025-11-09T12:00:00Z",
  "articles": [
    {
      "url": "https://example.com",
      "title": "Article Title",
      "issueDate": "2025-11-09",
      "category": "Newsletter",
      "removed": false,
      "tldrHidden": false,
      "read": { "isRead": false, "markedAt": null },
      "tldr": { "status": "unknown", "markdown": "", ... }
    }
  ],
  "issues": [...]
}
```

### Architecture Flow

```
User Action
  ↓
React Component (ArticleCard)
  ↓
Custom Hook (useArticleState)
  ↓
NEW: useSupabaseStorage hook (replaces useLocalStorage)
  ↓
Flask API endpoint (new: /api/storage/*)
  ↓
Supabase Client (sync, service_role key)
  ↓
Postgres Database
```

**Key Changes**:
- Replace `useLocalStorage` with `useSupabaseStorage` hook
- Add Flask API layer for storage operations
- Synchronous updates (grey out buttons during API calls)
- Cache-first reads (check DB before scraping, same as current)
- Browser-side sorting (no change)

### Verification Criteria

After migration is complete:

1. **All user flows work identically**:
   - Mark as read → article moves down in list
   - Remove → strikethrough, moves to bottom
   - Generate TLDR → markdown displays inline
   - Hide TLDR → article deprioritized
   - Page refresh → all states restored

2. **CSS states preserved**:
   - Unread articles: bold blue link
   - Read articles: muted gray
   - TLDR-hidden: 60% opacity
   - Removed: strikethrough, dashed border

3. **Sorting works**:
   - ArticleList sorts: unread → read → tldrHidden → removed
   - Within each group, original order preserved

4. **No regressions**:
   - Cache toggle works
   - Scraping works (cache-first)
   - TLDR generation works
   - Debug logs display

## What We're NOT Doing

- ❌ Backwards compatibility with localStorage (clean break)
- ❌ Data migration (users start fresh)
- ❌ Optimistic updates (synchronous only for simplicity)
- ❌ Normalized schema (JSONB blobs for 1:1 mapping)
- ❌ Multi-user support
- ❌ Row-level security policies
- ❌ Realtime subscriptions (polling/manual refresh only)
- ❌ Database-side sorting (browser sorting unchanged)
- ❌ Performance optimization (focus on correctness first)

## Implementation Approach

### High-Level Strategy

1. **Database First**: Create Supabase schema and test connectivity
2. **Backend API Layer**: Add Flask endpoints for storage operations
3. **Client Hook Replacement**: Create `useSupabaseStorage` to replace `useLocalStorage`
4. **Component Updates**: Swap hooks in components (minimal changes)
5. **Event System**: Adapt storage change events for new architecture
6. **Testing**: Verify all user flows work

### Key Design Decisions

**Cache-first reads** (user's choice):
- Before scraping, check DB for cached dates
- Same logic as current `isRangeCached()` function
- No change to scraping flow

**Synchronous updates** (user's choice):
- No optimistic updates
- Grey out buttons during API calls
- `disabled={isLoading}` on all action buttons
- Loading states: `isPending`, `loading`, etc.

**JSONB storage** (user's choice):
- Store entire DailyPayload as JSONB
- No schema changes to article structure
- Trivial to switch back to localStorage if needed

**Browser sorting** (user's choice):
- ArticleList continues to sort client-side
- No change to sorting logic
- Read state directly from fetched payloads

---

## Phase 1: Database Setup and Backend Foundation

### Overview
Set up Supabase database schema, verify connectivity, and create Flask API layer for storage operations.

### Changes Required

#### 1. Supabase Schema Creation

**Action**: Create tables via Supabase Dashboard SQL Editor

**SQL to run**:
```sql
-- Daily newsletter cache (stores DailyPayload JSONB)
CREATE TABLE daily_cache (
  date DATE PRIMARY KEY,
  payload JSONB NOT NULL,
  cached_at TIMESTAMPTZ DEFAULT NOW()
);

-- Application settings (stores cache:enabled, etc.)
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_daily_cache_date ON daily_cache(date DESC);
CREATE INDEX idx_settings_key ON settings(key);
```

**Verification**:
```sql
-- Test insert
INSERT INTO settings (key, value) VALUES ('cache:enabled', 'true');
INSERT INTO daily_cache (date, payload) VALUES
  ('2025-11-09', '{"date":"2025-11-09","articles":[],"issues":[]}');

-- Test read
SELECT * FROM settings WHERE key = 'cache:enabled';
SELECT * FROM daily_cache WHERE date = '2025-11-09';
```

#### 2. Supabase Client Setup (Backend)

**File**: `supabase_client.py` (new file)

**Purpose**: Initialize Supabase sync client for Flask backend

```python
from supabase import create_client, Client
import util

_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        url = util.resolve_env_var("SUPABASE_URL")
        key = util.resolve_env_var("SUPABASE_SERVICE_KEY")
        _supabase_client = create_client(url, key)
    return _supabase_client
```

**Why**: Singleton pattern prevents multiple client instances. Service role key provides full database access.

#### 3. Storage Service Layer

**File**: `storage_service.py` (new file)

**Purpose**: Abstraction layer for all storage operations

```python
import supabase_client

def get_setting(key):
    """
    Get setting value by key.

    >>> get_setting('cache:enabled')
    True
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('settings').select('value').eq('key', key).execute()

    if result.data:
        return result.data[0]['value']
    return None

def set_setting(key, value):
    """
    Set setting value by key (upsert).

    >>> set_setting('cache:enabled', False)
    {'key': 'cache:enabled', 'value': False, ...}
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('settings').upsert({
        'key': key,
        'value': value
    }).execute()

    return result.data[0] if result.data else None

def get_daily_payload(date):
    """
    Get cached payload for a specific date.

    >>> get_daily_payload('2025-11-09')
    {'date': '2025-11-09', 'articles': [...], ...}
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache').select('payload').eq('date', date).execute()

    if result.data:
        return result.data[0]['payload']
    return None

def set_daily_payload(date, payload):
    """
    Save or update daily payload (upsert).

    >>> set_daily_payload('2025-11-09', {'date': '2025-11-09', 'articles': [...]})
    {'date': '2025-11-09', 'payload': {...}, ...}
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache').upsert({
        'date': date,
        'payload': payload
    }).execute()

    return result.data[0] if result.data else None

def get_daily_payloads_range(start_date, end_date):
    """
    Get all cached payloads in date range (inclusive).

    >>> get_daily_payloads_range('2025-11-07', '2025-11-09')
    [{'date': '2025-11-09', ...}, {'date': '2025-11-08', ...}, ...]
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache') \
        .select('payload') \
        .gte('date', start_date) \
        .lte('date', end_date) \
        .order('date', desc=True) \
        .execute()

    return [row['payload'] for row in result.data]

def is_date_cached(date):
    """
    Check if a specific date exists in cache.

    >>> is_date_cached('2025-11-09')
    True
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache').select('date').eq('date', date).execute()

    return len(result.data) > 0
```

#### 4. Flask API Endpoints

**File**: `serve.py` (additions)

**New routes**:

```python
import storage_service

@app.route("/api/storage/setting/<key>", methods=["GET"])
def get_storage_setting(key):
    """Get setting value by key."""
    try:
        value = storage_service.get_setting(key)
        if value is None:
            return jsonify({"success": False, "error": "Setting not found"}), 404

        return jsonify({"success": True, "value": value})

    except Exception as e:
        util.log(
            "[serve.get_storage_setting] error key=%s error=%s",
            key, repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger
        )
        return jsonify({"success": False, "error": repr(e)}), 500

@app.route("/api/storage/setting/<key>", methods=["POST"])
def set_storage_setting(key):
    """Set setting value by key."""
    try:
        data = request.get_json()
        value = data['value']

        result = storage_service.set_setting(key, value)
        return jsonify({"success": True, "data": result})

    except Exception as e:
        util.log(
            "[serve.set_storage_setting] error key=%s error=%s",
            key, repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger
        )
        return jsonify({"success": False, "error": repr(e)}), 500

@app.route("/api/storage/daily/<date>", methods=["GET"])
def get_storage_daily(date):
    """Get cached payload for a specific date."""
    try:
        payload = storage_service.get_daily_payload(date)
        if payload is None:
            return jsonify({"success": False, "error": "Date not found"}), 404

        return jsonify({"success": True, "payload": payload})

    except Exception as e:
        util.log(
            "[serve.get_storage_daily] error date=%s error=%s",
            date, repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger
        )
        return jsonify({"success": False, "error": repr(e)}), 500

@app.route("/api/storage/daily/<date>", methods=["POST"])
def set_storage_daily(date):
    """Save or update daily payload."""
    try:
        data = request.get_json()
        payload = data['payload']

        result = storage_service.set_daily_payload(date, payload)
        return jsonify({"success": True, "data": result})

    except Exception as e:
        util.log(
            "[serve.set_storage_daily] error date=%s error=%s",
            date, repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger
        )
        return jsonify({"success": False, "error": repr(e)}), 500

@app.route("/api/storage/daily-range", methods=["POST"])
def get_storage_daily_range():
    """Get all cached payloads in date range."""
    try:
        data = request.get_json()
        start_date = data['start_date']
        end_date = data['end_date']

        payloads = storage_service.get_daily_payloads_range(start_date, end_date)
        return jsonify({"success": True, "payloads": payloads})

    except Exception as e:
        util.log(
            "[serve.get_storage_daily_range] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger
        )
        return jsonify({"success": False, "error": repr(e)}), 500

@app.route("/api/storage/is-cached/<date>", methods=["GET"])
def check_storage_is_cached(date):
    """Check if a specific date exists in cache."""
    try:
        is_cached = storage_service.is_date_cached(date)
        return jsonify({"success": True, "is_cached": is_cached})

    except Exception as e:
        util.log(
            "[serve.check_storage_is_cached] error date=%s error=%s",
            date, repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger
        )
        return jsonify({"success": False, "error": repr(e)}), 500
```

### Success Criteria

#### Automated Verification
- [ ] Database schema created successfully in Supabase Dashboard
- [ ] Test queries return expected results
- [ ] Flask server starts without errors: `start_server_and_watchdog`
- [ ] API endpoints respond to curl requests:
  ```bash
  # Test setting endpoints
  curl -X POST http://localhost:5001/api/storage/setting/cache:enabled \
    -H "Content-Type: application/json" \
    -d '{"value": true}'

  curl http://localhost:5001/api/storage/setting/cache:enabled

  # Test daily cache endpoints
  curl -X POST http://localhost:5001/api/storage/daily/2025-11-09 \
    -H "Content-Type: application/json" \
    -d '{"payload": {"date":"2025-11-09","articles":[],"issues":[]}}'

  curl http://localhost:5001/api/storage/daily/2025-11-09

  # Test range query
  curl -X POST http://localhost:5001/api/storage/daily-range \
    -H "Content-Type: application/json" \
    -d '{"start_date":"2025-11-07","end_date":"2025-11-09"}'

  # Test cache check
  curl http://localhost:5001/api/storage/is-cached/2025-11-09
  ```

#### Manual Verification
- [ ] Supabase Dashboard shows tables with correct schema
- [ ] All curl requests return valid JSON responses
- [ ] Setting values can be read back correctly
- [ ] Daily payloads can be stored and retrieved
- [ ] Date range queries return multiple payloads
- [ ] Cache existence check returns boolean

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Client Storage Abstraction Layer

### Overview
Create `useSupabaseStorage` hook to replace `useLocalStorage`, maintaining the same API interface so components require minimal changes.

### Changes Required

#### 1. Create useSupabaseStorage Hook

**File**: `client/src/hooks/useSupabaseStorage.js` (new file)

**Purpose**: Drop-in replacement for `useLocalStorage` with same API, but backed by Supabase

```javascript
import { useState, useCallback, useEffect } from 'react'

const changeListenersByKey = new Map()

function emitChange(key) {
  const listeners = changeListenersByKey.get(key)
  if (listeners) {
    listeners.forEach(listener => {
      try {
        listener()
      } catch (error) {
        console.error(`Storage listener failed: ${error.message}`)
      }
    })
  }

  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('supabase-storage-change', { detail: { key } }))
  }
}

function subscribe(key, listener) {
  if (!changeListenersByKey.has(key)) {
    changeListenersByKey.set(key, new Set())
  }
  changeListenersByKey.get(key).add(listener)

  return () => {
    const listeners = changeListenersByKey.get(key)
    if (listeners) {
      listeners.delete(listener)
      if (listeners.size === 0) {
        changeListenersByKey.delete(key)
      }
    }
  }
}

async function readValue(key, defaultValue) {
  if (typeof window === 'undefined') return defaultValue

  try {
    // Settings key (cache:enabled, etc.)
    if (key.startsWith('cache:')) {
      const response = await window.fetch(`/api/storage/setting/${key}`)
      const data = await response.json()

      if (data.success) {
        return data.value
      }

      return defaultValue
    }

    // Daily cache key (newsletters:scrapes:{date})
    if (key.startsWith('newsletters:scrapes:')) {
      const date = key.split(':')[2]
      const response = await window.fetch(`/api/storage/daily/${date}`)
      const data = await response.json()

      if (data.success) {
        return data.payload
      }

      return defaultValue
    }

    console.warn(`Unknown storage key pattern: ${key}`)
    return defaultValue

  } catch (error) {
    console.error(`Failed to read from storage: ${error.message}`)
    return defaultValue
  }
}

async function writeValue(key, value) {
  if (typeof window === 'undefined') return

  try {
    // Settings key
    if (key.startsWith('cache:')) {
      const response = await window.fetch(`/api/storage/setting/${key}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value })
      })

      const data = await response.json()
      if (!data.success) {
        throw new Error(data.error || 'Failed to write setting')
      }

      emitChange(key)
      return
    }

    // Daily cache key
    if (key.startsWith('newsletters:scrapes:')) {
      const date = key.split(':')[2]
      const response = await window.fetch(`/api/storage/daily/${date}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload: value })
      })

      const data = await response.json()
      if (!data.success) {
        throw new Error(data.error || 'Failed to write daily cache')
      }

      emitChange(key)
      return
    }

    throw new Error(`Unknown storage key pattern: ${key}`)

  } catch (error) {
    console.error(`Failed to persist to storage: ${error.message}`)
    throw error
  }
}

export function useSupabaseStorage(key, defaultValue) {
  const [value, setValue] = useState(defaultValue)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Initial load
  useEffect(() => {
    let cancelled = false

    readValue(key, defaultValue).then(loadedValue => {
      if (!cancelled) {
        setValue(loadedValue)
        setLoading(false)
      }
    }).catch(err => {
      if (!cancelled) {
        console.error(`Failed to load storage value for ${key}:`, err)
        setError(err)
        setValue(defaultValue)
        setLoading(false)
      }
    })

    return () => {
      cancelled = true
    }
  }, [key, defaultValue])

  // Subscribe to changes
  useEffect(() => {
    const handleChange = () => {
      readValue(key, defaultValue).then(newValue => {
        setValue(newValue)
      }).catch(err => {
        console.error(`Failed to reload storage value for ${key}:`, err)
      })
    }

    return subscribe(key, handleChange)
  }, [key, defaultValue])

  // Setter function
  const setValueAsync = useCallback(async (nextValue) => {
    if (typeof window === 'undefined') return

    setLoading(true)
    setError(null)

    try {
      const previous = value
      const resolved = typeof nextValue === 'function' ? nextValue(previous) : nextValue

      if (resolved === previous) {
        setLoading(false)
        return
      }

      await writeValue(key, resolved)
      setValue(resolved)
      setLoading(false)

    } catch (err) {
      console.error(`Failed to set storage value for ${key}:`, err)
      setError(err)
      setLoading(false)
      throw err
    }
  }, [key, value])

  // Remove function
  const remove = useCallback(async () => {
    await setValueAsync(undefined)
  }, [setValueAsync])

  return [value, setValueAsync, remove, { loading, error }]
}
```

**Key Design Points**:
- Same API as `useLocalStorage`: `[value, setValue, remove]` (plus loading/error)
- Async reads on mount (shows loading state)
- Async writes (throws on error for caller to handle)
- Event system for cross-component sync
- Supports functional updates: `setValue(prev => ({ ...prev, ...changes }))`

#### 2. Update storageKeys Helper

**File**: `client/src/lib/storageKeys.js`

**Changes**: No changes needed - key patterns remain the same

```javascript
// Existing code unchanged
export const STORAGE_KEYS = {
  CACHE_ENABLED: 'cache:enabled'
}

export function getNewsletterScrapeKey(date) {
  return `newsletters:scrapes:${date}`
}
```

#### 3. Create Storage API Client

**File**: `client/src/lib/storageApi.js` (new file)

**Purpose**: API client for direct storage operations (used by scraper.js)

```javascript
export async function isDateCached(date) {
  const response = await window.fetch(`/api/storage/is-cached/${date}`)
  const data = await response.json()

  if (data.success) {
    return data.is_cached
  }

  throw new Error(data.error || 'Failed to check cache')
}

export async function getDailyPayload(date) {
  const response = await window.fetch(`/api/storage/daily/${date}`)
  const data = await response.json()

  if (data.success) {
    return data.payload
  }

  return null
}

export async function setDailyPayload(date, payload) {
  const response = await window.fetch(`/api/storage/daily/${date}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payload })
  })

  const data = await response.json()

  if (!data.success) {
    throw new Error(data.error || 'Failed to save payload')
  }

  return data.data
}

export async function getDailyPayloadsRange(startDate, endDate) {
  const response = await window.fetch('/api/storage/daily-range', {
    method: 'POST',
    headers: { 'Content-Type: application/json' },
    body: JSON.stringify({ start_date: startDate, end_date: endDate })
  })

  const data = await response.json()

  if (data.success) {
    return data.payloads
  }

  throw new Error(data.error || 'Failed to load payloads')
}
```

### Success Criteria

#### Automated Verification
- [ ] Flask server running: `start_server_and_watchdog`
- [ ] No TypeScript/ESLint errors: `cd client && npm run build`

#### Manual Verification
- [ ] `useSupabaseStorage` hook exports correctly (no import errors)
- [ ] Hook returns `[value, setValue, remove, { loading, error }]` tuple
- [ ] storageApi exports all functions
- [ ] No console errors when importing new files

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Update Core Hooks

### Overview
Replace `useLocalStorage` with `useSupabaseStorage` in `useArticleState` and `useSummary` hooks. Add loading states and error handling.

### Changes Required

#### 1. Update useArticleState Hook

**File**: `client/src/hooks/useArticleState.js`

**Changes**:
```javascript
// BEFORE
import { useLocalStorage } from './useLocalStorage'
import { getNewsletterScrapeKey } from '../lib/storageKeys'

const storageKey = getNewsletterScrapeKey(date)
const [payload, setPayload] = useLocalStorage(storageKey, null)
```

```javascript
// AFTER
import { useSupabaseStorage } from './useSupabaseStorage'
import { getNewsletterScrapeKey } from '../lib/storageKeys'

const storageKey = getNewsletterScrapeKey(date)
const [payload, setPayload, , { loading, error }] = useSupabaseStorage(storageKey, null)
```

**New exports**:
```javascript
// Add to return object
return {
  article,
  state,
  loading,  // NEW
  error,    // NEW
  markAsRead,
  markAsUnread,
  toggleRead,
  isRead,
  setRemoved,
  toggleRemove,
  isRemoved,
  setTldrHidden,
  markTldrHidden,
  unmarkTldrHidden,
  isTldrHidden,
  updateArticle
}
```

**Why**: Components need loading/error states to grey out buttons and show errors.

#### 2. Update useSummary Hook

**File**: `client/src/hooks/useSummary.js`

**Changes**: Import `useSupabaseStorage` instead of `useLocalStorage`

```javascript
// This file already uses useArticleState, which now uses useSupabaseStorage
// No direct changes needed, but it inherits loading/error states from useArticleState
```

**New behavior**: Loading states from `useArticleState` will affect TLDR button state.

### Success Criteria

#### Automated Verification
- [ ] No build errors: `cd client && npm run build`
- [ ] No import errors
- [ ] TypeScript/ESLint passes

#### Manual Verification
- [ ] ArticleCard shows loading spinner when reading article state
- [ ] Action buttons greyed out during loading
- [ ] Error messages display if storage fails
- [ ] Console shows no errors during normal operation

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 4: Update Scraper Logic

### Overview
Replace direct localStorage calls in `scraper.js` with storage API calls. Maintain cache-first behavior.

### Changes Required

#### 1. Update scraper.js

**File**: `client/src/lib/scraper.js`

**Replace all localStorage calls**:

```javascript
// BEFORE
import { getNewsletterScrapeKey } from './storageKeys'

function isRangeCached(startDate, endDate, cacheEnabled) {
  if (!cacheEnabled) return false

  const dates = computeDateRange(startDate, endDate)

  for (const date of dates) {
    const key = getNewsletterScrapeKey(date)
    if (localStorage.getItem(key) === null) {  // OLD
      return false
    }
  }

  return true
}
```

```javascript
// AFTER
import { getNewsletterScrapeKey } from './storageKeys'
import * as storageApi from './storageApi'

async function isRangeCached(startDate, endDate, cacheEnabled) {
  if (!cacheEnabled) return false

  const dates = computeDateRange(startDate, endDate)

  for (const date of dates) {
    const isCached = await storageApi.isDateCached(date)  // NEW
    if (!isCached) {
      return false
    }
  }

  return true
}
```

**Update loadFromCache**:

```javascript
// BEFORE
function loadFromCache(startDate, endDate) {
  const dates = computeDateRange(startDate, endDate)
  const payloads = []

  for (const date of dates) {
    const key = getNewsletterScrapeKey(date)
    const raw = localStorage.getItem(key)  // OLD
    if (raw) {
      const payload = JSON.parse(raw)
      payloads.push(payload)
    }
  }

  // ...
}
```

```javascript
// AFTER
async function loadFromCache(startDate, endDate) {
  const payloads = await storageApi.getDailyPayloadsRange(startDate, endDate)  // NEW

  if (!payloads || payloads.length === 0) {
    return null
  }

  // ... rest unchanged
}
```

**Update mergeWithCache**:

```javascript
// BEFORE
function mergeWithCache(payloads) {
  return payloads.map(payload => {
    const key = getNewsletterScrapeKey(payload.date)
    const raw = localStorage.getItem(key)  // OLD

    if (raw) {
      const existing = JSON.parse(raw)
      // ... merge logic
      localStorage.setItem(key, JSON.stringify(merged))  // OLD
    } else {
      localStorage.setItem(key, JSON.stringify(payload))  // OLD
    }

    return merged
  })
}
```

```javascript
// AFTER
async function mergeWithCache(payloads) {
  const merged = []

  for (const payload of payloads) {
    const existing = await storageApi.getDailyPayload(payload.date)  // NEW

    if (existing) {
      const mergedPayload = {
        ...payload,
        articles: payload.articles.map(article => {
          const existingArticle = existing.articles?.find(a => a.url === article.url)
          if (existingArticle) {
            return {
              ...article,
              tldr: existingArticle.tldr || article.tldr,
              read: existingArticle.read || article.read,
              removed: existingArticle.removed ?? article.removed,
              tldrHidden: existingArticle.tldrHidden ?? article.tldrHidden
            }
          }
          return article
        })
      }

      await storageApi.setDailyPayload(payload.date, mergedPayload)  // NEW
      merged.push(mergedPayload)
    } else {
      await storageApi.setDailyPayload(payload.date, payload)  // NEW
      merged.push(payload)
    }
  }

  return merged
}
```

**Update scrapeNewsletters function**:

```javascript
// BEFORE
export async function scrapeNewsletters(startDate, endDate, cacheEnabled = true) {
  if (isRangeCached(startDate, endDate, cacheEnabled)) {  // OLD: sync
    const cached = loadFromCache(startDate, endDate)  // OLD: sync
    // ...
  }

  // ... API call

  const mergedPayloads = cacheEnabled ? mergeWithCache(payloads) : payloads  // OLD: sync
  // ...
}
```

```javascript
// AFTER
export async function scrapeNewsletters(startDate, endDate, cacheEnabled = true) {
  if (await isRangeCached(startDate, endDate, cacheEnabled)) {  // NEW: async
    const cached = await loadFromCache(startDate, endDate)  // NEW: async
    // ...
  }

  // ... API call

  const mergedPayloads = cacheEnabled ? await mergeWithCache(payloads) : payloads  // NEW: async
  // ...
}
```

**Why**: All storage operations are now async. Functions that call storage must be async and await.

### Success Criteria

#### Automated Verification
- [ ] No build errors: `cd client && npm run build`
- [ ] No async/await errors
- [ ] All functions properly await storage calls

#### Manual Verification
- [ ] Cache check works before scraping
- [ ] Scraping loads from cache when available
- [ ] Fresh scrapes merge with existing data
- [ ] User state preserved across scrapes
- [ ] Console shows no errors

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 5: Update Components

### Overview
Update components to handle loading states and replace `useLocalStorage` with `useSupabaseStorage`.

### Changes Required

#### 1. Update CacheToggle Component

**File**: `client/src/components/CacheToggle.jsx`

**Changes**:

```javascript
// BEFORE
import { useLocalStorage } from '../hooks/useLocalStorage'

const [enabled, setEnabled] = useLocalStorage('cache:enabled', true)
```

```javascript
// AFTER
import { useSupabaseStorage } from '../hooks/useSupabaseStorage'

const [enabled, setEnabled, , { loading }] = useSupabaseStorage('cache:enabled', true)
```

**UI changes**:

```jsx
{/* BEFORE */}
<input
  type="checkbox"
  checked={enabled}
  onChange={(e) => setEnabled(e.target.checked)}
/>

{/* AFTER */}
<input
  type="checkbox"
  checked={enabled}
  disabled={loading}
  onChange={(e) => setEnabled(e.target.checked)}
/>
```

#### 2. Update ScrapeForm Component

**File**: `client/src/components/ScrapeForm.jsx`

**Changes**:

```javascript
// BEFORE
import { useLocalStorage } from '../hooks/useLocalStorage'

const [cacheEnabled] = useLocalStorage('cache:enabled', true)
```

```javascript
// AFTER
import { useSupabaseStorage } from '../hooks/useSupabaseStorage'

const [cacheEnabled] = useSupabaseStorage('cache:enabled', true)
```

**Note**: Read-only usage, no other changes needed.

#### 3. Update ArticleCard Component

**File**: `client/src/components/ArticleCard.jsx`

**Changes**: Handle loading states from hooks

```javascript
// Get loading states from hooks
const { toggleRead, toggleRemove, isRead, isRemoved, loading: stateLoading } = useArticleState(article.issueDate, article.url)
const tldr = useSummary(article.issueDate, article.url, 'tldr')
```

**UI changes**:

```jsx
{/* BEFORE */}
<a
  href={article.url}
  target="_blank"
  rel="noopener noreferrer"
  onClick={handleLinkClick}
  tabIndex={isRemoved ? -1 : 0}
>
  {article.title || article.url}
</a>

{/* AFTER */}
<a
  href={article.url}
  target="_blank"
  rel="noopener noreferrer"
  onClick={handleLinkClick}
  tabIndex={isRemoved ? -1 : 0}
  className={stateLoading ? 'loading' : ''}
>
  {article.title || article.url}
</a>

{/* Add loading styles */}
<button
  className={`article-btn remove-article-btn ${isRemoved ? 'removed' : ''}`}
  onClick={toggleRemove}
  disabled={stateLoading}
>
  {isRemoved ? 'Restore' : 'Remove'}
</button>

<button
  className={`article-btn tldr-btn ${tldr.isAvailable ? 'loaded' : ''} ${tldr.expanded ? 'expanded' : ''}`}
  onClick={handleTldrClick}
  disabled={stateLoading || tldr.loading}
>
  {tldr.label}
</button>
```

**CSS changes** (`ArticleCard.css`):

```css
/* Add loading styles */
.article-card a.loading {
  opacity: 0.6;
  cursor: wait;
}

.article-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

#### 4. Update ArticleList Component

**File**: `client/src/components/ArticleList.jsx`

**Changes**: Listen to new storage event

```javascript
// BEFORE
useEffect(() => {
  const handleStorageChange = () => {
    setStorageVersion(v => v + 1)
  }

  window.addEventListener('local-storage-change', handleStorageChange)  // OLD
  return () => window.removeEventListener('local-storage-change', handleStorageChange)
}, [])
```

```javascript
// AFTER
useEffect(() => {
  const handleStorageChange = () => {
    setStorageVersion(v => v + 1)
  }

  window.addEventListener('supabase-storage-change', handleStorageChange)  // NEW
  return () => window.removeEventListener('supabase-storage-change', handleStorageChange)
}, [])
```

**Update getArticleState**:

```javascript
// BEFORE
const getArticleState = (article) => {
  const storageKey = getNewsletterScrapeKey(article.issueDate)
  const raw = localStorage.getItem(storageKey)  // OLD
  const payload = JSON.parse(raw)
  // ...
}
```

```javascript
// AFTER
import * as storageApi from '../lib/storageApi'

// Make sortedArticles computation async-safe
const [articleStates, setArticleStates] = useState({})

useEffect(() => {
  // Fetch all article states when articles change
  async function loadStates() {
    const states = {}

    for (const article of articles) {
      const payload = await storageApi.getDailyPayload(article.issueDate)
      if (payload) {
        const liveArticle = payload.articles?.find(a => a.url === article.url)
        if (liveArticle) {
          if (liveArticle.removed) states[article.url] = 3
          else if (liveArticle.tldrHidden) states[article.url] = 2
          else if (liveArticle.read?.isRead) states[article.url] = 1
          else states[article.url] = 0
        }
      }
    }

    setArticleStates(states)
  }

  loadStates()
}, [articles, storageVersion])

const sortedArticles = useMemo(() => {
  return [...articles].sort((a, b) => {
    const stateA = articleStates[a.url] ?? 0
    const stateB = articleStates[b.url] ?? 0

    if (stateA !== stateB) return stateA - stateB

    return (a.originalOrder ?? 0) - (b.originalOrder ?? 0)
  })
}, [articles, articleStates])
```

**Why**: Sorting now uses pre-fetched states from async storage.

#### 5. Update ResultsDisplay Component

**File**: `client/src/components/ResultsDisplay.jsx`

**Changes**: Replace `useLocalStorage` with `useSupabaseStorage`

```javascript
// BEFORE
import { useLocalStorage } from '../hooks/useLocalStorage'

const [livePayload] = useLocalStorage(
  getNewsletterScrapeKey(payload.date),
  payload
)
```

```javascript
// AFTER
import { useSupabaseStorage } from '../hooks/useSupabaseStorage'

const [livePayload, , , { loading }] = useSupabaseStorage(
  getNewsletterScrapeKey(payload.date),
  payload
)
```

**UI changes**:

```jsx
{/* Show loading indicator */}
{loading && <div className="loading-indicator">Loading...</div>}

<ArticleList articles={articles} />
```

#### 6. Update App Component

**File**: `client/src/App.jsx`

**Changes**: Update initial cache load to async

```javascript
// BEFORE
useEffect(() => {
  const today = new Date()
  const threeDaysAgo = new Date(today)
  threeDaysAgo.setDate(today.getDate() - 3)

  const endDate = today.toISOString().split('T')[0]
  const startDate = threeDaysAgo.toISOString().split('T')[0]

  const cached = loadFromCache(startDate, endDate)  // OLD: sync
  if (cached) {
    setResults(cached)
  }
}, [])
```

```javascript
// AFTER
import * as storageApi from './lib/storageApi'

useEffect(() => {
  const today = new Date()
  const threeDaysAgo = new Date(today)
  threeDaysAgo.setDate(today.getDate() - 3)

  const endDate = today.toISOString().split('T')[0]
  const startDate = threeDaysAgo.toISOString().split('T')[0]

  // Load from storage asynchronously
  storageApi.getDailyPayloadsRange(startDate, endDate)
    .then(payloads => {
      if (payloads && payloads.length > 0) {
        setResults({
          success: true,
          payloads,
          source: 'Cached',
          stats: null
        })
      }
    })
    .catch(err => {
      console.error('Failed to load cached results:', err)
    })
}, [])
```

### Success Criteria

#### Automated Verification
- [ ] No build errors: `cd client && npm run build`
- [ ] No TypeScript/ESLint errors
- [ ] No console errors on page load

#### Manual Verification
- [ ] All components render without errors
- [ ] Loading states show correctly (greyed buttons, loading text)
- [ ] Cache toggle works (checkbox enables/disables)
- [ ] Initial page load shows cached results (if any exist)
- [ ] All buttons respond correctly when not loading
- [ ] Error states display appropriately

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 6: End-to-End Testing and Verification

### Overview
Test all user flows to ensure complete feature parity with localStorage implementation.

### Manual Test Plan

#### Test 1: Cache Toggle
1. Open app in browser
2. Observe cache toggle checkbox state
3. Click checkbox to disable cache
4. **Expected**: Checkbox updates, setting saved to DB
5. Refresh page (Cmd+R)
6. **Expected**: Checkbox reflects saved state
7. Click checkbox to enable cache
8. **Expected**: Checkbox updates, setting saved to DB

#### Test 2: Newsletter Scraping (Cache Miss)
1. Ensure cache is empty for date range (or use future dates)
2. Enter start/end dates (e.g., yesterday and today)
3. Click "Scrape Newsletters"
4. **Expected**:
   - Progress bar shows
   - "Scraping..." button text
   - Results display after API call
   - Articles visible, grouped by date/issue
5. Verify in Supabase Dashboard that `daily_cache` has new rows

#### Test 3: Newsletter Scraping (Cache Hit)
1. Use same date range as Test 2
2. Click "Scrape Newsletters"
3. **Expected**:
   - Results load instantly from cache (no API call)
   - Source shows "Cached"
   - Same articles display

#### Test 4: Mark Article as Read
1. Find an unread article (bold blue link)
2. Click article title link
3. **Expected**:
   - Link opens in new tab
   - Article link becomes muted gray
   - Article moves down in list (below unread articles)
   - Button disabled during save (grey)
   - Button re-enables after save
4. Refresh page (Cmd+R)
5. **Expected**: Article still shows as read (muted gray, sorted below unread)

#### Test 5: Remove Article
1. Find any article
2. Hover to show action buttons
3. Click "Remove" button
4. **Expected**:
   - Button disabled during save
   - Article gets strikethrough + dashed border
   - Article moves to bottom of list
   - Button changes to "Restore"
   - TLDR button hides
5. Refresh page (Cmd+R)
6. **Expected**: Article still removed with strikethrough

#### Test 6: Restore Removed Article
1. Find removed article from Test 5
2. Click "Restore" button
3. **Expected**:
   - Button disabled during save
   - Strikethrough/dashed border removed
   - Article moves up in list (based on read state)
   - Button changes to "Remove"
   - TLDR button visible again

#### Test 7: Generate TLDR
1. Find an article with no TLDR
2. Click "TLDR" button
3. **Expected**:
   - Button shows "Loading..."
   - Button disabled
   - After API response: TLDR displays inline
   - Button turns green, shows "Available"
   - Article marked as read
4. Refresh page (Cmd+R)
5. **Expected**: TLDR button green, says "Available"
6. Click "Available" button
7. **Expected**: TLDR expands inline, button says "Hide"

#### Test 8: Hide TLDR
1. With TLDR expanded from Test 7
2. Click "Hide" button
3. **Expected**:
   - TLDR collapses
   - Article gets 60% opacity + gray background
   - Article moves down in list (below read articles)
   - Button disabled during save
4. Refresh page (Cmd+R)
5. **Expected**: Article still has 60% opacity, sorted below read articles

#### Test 9: Expand Hidden TLDR
1. Find article with hidden TLDR from Test 8
2. Click TLDR button (shows "Available")
3. **Expected**:
   - TLDR expands
   - Opacity returns to 100%
   - Article moves up in list (read state, not hidden)
   - Button disabled during save

#### Test 10: Article Sorting Verification
1. Create articles in all 4 states:
   - Unread (default)
   - Read (click link)
   - TLDR-hidden (hide TLDR)
   - Removed (click remove)
2. **Expected order from top to bottom**:
   - Unread articles (bold blue)
   - Read articles (muted gray)
   - TLDR-hidden articles (60% opacity)
   - Removed articles (strikethrough)
3. Refresh page (Cmd+R)
4. **Expected**: Same order maintained

#### Test 11: Scrape with Existing Data
1. Scrape a date range that already has cached data
2. **Expected**:
   - Fresh scrape happens
   - New articles appear
   - Existing article states preserved (read/removed/tldr)
   - User modifications not lost

#### Test 12: Error Handling
1. Stop Flask backend: `kill_server_and_watchdog`
2. Try to mark article as read
3. **Expected**:
   - Error message displays
   - Article state doesn't change
   - Console shows network error
4. Restart backend: `start_server_and_watchdog`
5. Try action again
6. **Expected**: Action succeeds

### Automated Test Checklist

Run these commands to verify no regressions:

```bash
# Backend tests
source ./setup.sh
start_server_and_watchdog
sleep 2
print_server_and_watchdog_pids

# Test all storage API endpoints
curl http://localhost:5001/api/storage/setting/cache:enabled
curl -X POST http://localhost:5001/api/storage/setting/cache:enabled \
  -H "Content-Type: application/json" \
  -d '{"value": false}'

curl http://localhost:5001/api/storage/is-cached/2025-11-09
curl http://localhost:5001/api/storage/daily/2025-11-09

curl -X POST http://localhost:5001/api/storage/daily-range \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2025-11-07","end_date":"2025-11-09"}'

# Frontend build
cd client
npm run build

# Check for console errors
npm run dev
# Open http://localhost:3000 in browser
# Check DevTools console for errors
```

### Success Criteria

#### Automated Verification
- [ ] All curl requests succeed with `{"success": true}`
- [ ] Frontend builds without errors
- [ ] No console errors on page load
- [ ] No network errors in DevTools Network tab

#### Manual Verification
- [ ] All 12 test scenarios pass
- [ ] All CSS states display correctly
- [ ] Article sorting works correctly
- [ ] Page refresh preserves all states
- [ ] Error handling works (graceful degradation)
- [ ] Loading states show correctly (disabled buttons, loading text)
- [ ] No visual regressions (compare side-by-side with localStorage version)

**Implementation Note**: After completing this phase and all verification passes, the migration is complete. No further phases needed.

---

## References

- Original research: `thoughts/2025-11-08-migrate-client-localstorage-to-server-supabase/research/supabase-database.md`
- Current architecture: `ARCHITECTURE.md`
- Project structure: `PROJECT_STRUCTURE.md`
- localStorage usage analysis: From research agents (completed in this session)
- CSS states mapping: From research agents (completed in this session)
- API patterns: From research agents (completed in this session)

---

## Risk Assessment

### High Risk Items
1. **Async everywhere**: Every storage operation now async - potential for race conditions
   - **Mitigation**: Test thoroughly, use loading states consistently
2. **Network latency**: User actions take 50-200ms instead of 0ms
   - **Mitigation**: Grey out buttons, show loading states clearly
3. **Error handling**: Network failures can break user flows
   - **Mitigation**: Try/catch everywhere, show user-friendly errors

### Medium Risk Items
1. **Data loss**: If migration fails mid-operation
   - **Mitigation**: Users start fresh (no migration), acceptable per requirements
2. **Event system**: `supabase-storage-change` must trigger re-sorts
   - **Mitigation**: Test event dispatching thoroughly in ArticleList
3. **Sorting performance**: Async state fetching for 100+ articles
   - **Mitigation**: Pre-fetch all states in ArticleList useEffect

### Low Risk Items
1. **Schema changes**: JSONB is flexible, easy to modify later
2. **API changes**: Backend API is isolated, easy to modify
3. **Rollback**: Can switch back to localStorage by reverting hook imports

---

## Notes

- **No data migration**: Users start with empty database (acceptable per requirements)
- **No optimistic updates**: All updates wait for server confirmation (user's choice)
- **Simple schema**: Two tables, minimal complexity
- **Cache-first**: Same behavior as current localStorage implementation
- **Browser sorting**: No changes to sorting logic
- **Service role key**: Provides full database access for backend operations
- **Single-user**: No multi-user considerations
- **Free tier**: No scale concerns, simple implementation prioritized
