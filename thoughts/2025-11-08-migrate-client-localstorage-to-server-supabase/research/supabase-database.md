---
last-updated: 2025-11-08 10:46, 8539791
---
# Supabase Database Migration Research

Research for migrating TLDRScraper's localStorage-based state management to Supabase (PostgreSQL) backend.

**Date:** 2025-11-08
**Purpose:** Pre-implementation research for 1:1 localStorage → Supabase migration

---

## Table of Contents

1. [Supabase Platform Overview](#1-supabase-platform-overview)
2. [Supabase Python API Setup](#2-supabase-python-api-setup)
3. [Current localStorage Structure Analysis](#3-current-localstorage-structure-analysis)
4. [Database Design Patterns](#4-database-design-patterns)
5. [Migration Strategy](#5-migration-strategy)
6. [Security Architecture](#6-security-architecture)
7. [Real-time Synchronization](#7-real-time-synchronization)
8. [Client-Side DOM State Management](#8-client-side-dom-state-management)
9. [Performance Considerations](#9-performance-considerations)
10. [Implementation Requirements](#10-implementation-requirements)

---

## 1. Supabase Platform Overview

### What is Supabase?

Supabase is a comprehensive Postgres development platform that provides:
- **Full PostgreSQL Database**: 30+ years of proven stability, open-source
- **Auto-generated REST API**: PostgREST automatically exposes database as RESTful API
- **Real-time Subscriptions**: Elixir-based realtime server for database change notifications via WebSockets
- **Authentication**: GoTrue JWT-based auth API
- **File Storage**: S3-compatible storage with Postgres-backed permissions
- **Edge Functions**: Deno-based serverless functions

### Architecture Components

```
┌─────────────────────────────────────────────────────┐
│                 Supabase Stack                       │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐                │
│  │  PostgreSQL  │  │  PostgREST   │ ← Auto API     │
│  │  (Database)  │  │  (REST API)  │                │
│  └──────────────┘  └──────────────┘                │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐                │
│  │   Realtime   │  │    GoTrue    │                │
│  │ (WebSockets) │  │    (Auth)    │                │
│  └──────────────┘  └──────────────┘                │
└─────────────────────────────────────────────────────┘
                       ▲
                       │ Python Client (supabase-py)
                       ▼
              ┌─────────────────┐
              │  Flask Backend  │
              └─────────────────┘
```

### Key Advantages for This Project

1. **Automatic API Generation**: No need to manually create CRUD endpoints
2. **Built-in Row Level Security (RLS)**: Granular per-row access control
3. **Real-time Updates**: Built-in WebSocket support for live data synchronization
4. **PostgreSQL Features**: JSONB, full-text search, indexes, materialized views
5. **Open Source**: No vendor lock-in, can self-host if needed

---

## 2. Supabase Python API Setup

### Installation

```bash
uv add supabase
```

**Current Version:** Released Nov 6, 2025
**Python Requirement:** >= 3.9

### Basic Setup

```python
import os
from supabase import create_client, Client

# Environment variables (already available in this project)
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")  # For backend

# Initialize client
supabase: Client = create_client(url, key)
```


### Connection Pooling

Supabase provides built-in connection pooling:

- **Session Mode**: Connection assigned until client disconnects (default)
- **Transaction Mode**: Connection assigned per transaction (ideal for serverless)

For Flask (long-lived server), Session mode is appropriate. Supabase handles pooling automatically.

**Best Practice:** Use application-side pooling for optimal performance:
```python
# Supabase client maintains connection pool internally
# No additional configuration needed for basic use cases
```

---

## 4. Database Design Patterns

### Normalized vs. JSONB: Decision Matrix

#### Performance Comparison

**Research Finding:** PostgreSQL can be **~2000x slower** with JSONB for queries that would use indexed columns in normalized tables.

**JSONB Disadvantages:**
- No statistics tracking → poor query optimization
- 2x+ storage overhead (keys duplicated per row)
- Write-heavy workloads suffer
- Cannot efficiently index nested fields without specific GIN indexes

**JSONB Advantages:**
- Flexible schema for optional/variable fields
- Simpler for deeply nested data
- Good for read-mostly, schema-less data

**Recommendation for This Project:** **Hybrid Normalized + JSONB**

```sql
-- Normalized core fields (frequently queried)
CREATE TABLE articles (
  url TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  issue_date DATE NOT NULL,
  category TEXT NOT NULL,
  source_id TEXT NOT NULL,

  -- JSONB for optional/variable fields
  metadata JSONB,

  -- User state (normalized for query performance)
  removed BOOLEAN DEFAULT FALSE,
  tldr_hidden BOOLEAN DEFAULT FALSE,
  is_read BOOLEAN DEFAULT FALSE,
  read_marked_at TIMESTAMPTZ,

  -- TLDR state (could be JSONB or separate table)
  tldr_status TEXT DEFAULT 'unknown',
  tldr_markdown TEXT,
  tldr_effort TEXT,
  tldr_checked_at TIMESTAMPTZ,
  tldr_error_message TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_articles_issue_date ON articles(issue_date);
CREATE INDEX idx_articles_source_id ON articles(source_id);
CREATE INDEX idx_articles_removed ON articles(removed) WHERE removed = TRUE;
CREATE INDEX idx_articles_is_read ON articles(is_read);

-- GIN index for JSONB queries (if needed)
CREATE INDEX idx_articles_metadata ON articles USING GIN (metadata);
```

### Schema Design Recommendation

#### Tables

**1. `articles` Table**
```sql
CREATE TABLE articles (
  url TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  issue_date DATE NOT NULL,
  category TEXT NOT NULL,
  source_id TEXT NOT NULL,
  section TEXT,
  section_emoji TEXT,
  section_order INTEGER,
  newsletter_type TEXT,

  -- User state
  removed BOOLEAN DEFAULT FALSE,
  tldr_hidden BOOLEAN DEFAULT FALSE,
  is_read BOOLEAN DEFAULT FALSE,
  read_marked_at TIMESTAMPTZ,

  -- TLDR data
  tldr_status TEXT DEFAULT 'unknown' CHECK (tldr_status IN ('unknown', 'creating', 'available', 'error')),
  tldr_markdown TEXT,
  tldr_effort TEXT CHECK (tldr_effort IN ('minimal', 'low', 'medium', 'high')),
  tldr_checked_at TIMESTAMPTZ,
  tldr_error_message TEXT,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**2. `issues` Table**
```sql
CREATE TABLE issues (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  source_id TEXT NOT NULL,
  category TEXT NOT NULL,
  title TEXT,
  subtitle TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(date, source_id)
);
```

**3. `daily_cache` Table (Optional - for caching full payloads)**
```sql
CREATE TABLE daily_cache (
  date DATE PRIMARY KEY,
  cached_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**4. `user_preferences` Table**
```sql
CREATE TABLE user_preferences (
  id SERIAL PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- For cache:enabled setting
INSERT INTO user_preferences (key, value)
VALUES ('cache:enabled', 'true'::jsonb);
```

#### Database Functions

**Auto-update timestamp:**
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_articles_updated_at
  BEFORE UPDATE ON articles
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
```

---

## 5. Migration Strategy

### Phased Approach

#### Phase 1: Backend Setup (No Client Changes)

1. **Set up Supabase database**
   - Create tables with schema above
   - Apply migrations using Supabase CLI
   - Configure RLS policies (initially permissive)

2. **Create data access layer**
   - New module: `supabase_client.py`
   - Service functions matching existing cache operations
   - Maintain backwards compatibility with localStorage flow

3. **Add write-through caching**
   - Backend writes to Supabase after scraping
   - Responses still include full payload (client continues using localStorage)
   - Build up database in background

#### Phase 2: Hybrid Read (Fallback to localStorage)

1. **New API endpoints**
   - `GET /api/user-state/{date}` - Fetch DailyPayload from database
   - `POST /api/user-state/article` - Update article state
   - `GET /api/preferences` - Get user preferences

2. **Client changes**
   - Check database first, fall back to localStorage
   - Write to both database and localStorage
   - Gradual migration of stored data

#### Phase 3: Database as Primary Source

1. **Remove localStorage writes** (reads remain for backwards compat)
2. **All state mutations go through API**
3. **Client subscribes to realtime updates** (optional)

#### Phase 4: Remove localStorage Dependencies

1. **Client uses database exclusively**
2. **Remove localStorage hooks** from state management
3. **localStorage only for transient UI state** (e.g., expanded panels)

### Data Migration Script

```python
import json
from pathlib import Path
from supabase import create_client

def migrate_localstorage_export_to_supabase(export_file: Path):
    """
    Migrate exported localStorage data to Supabase.

    Export format (from browser console):
    {
      "newsletters:scrapes:2024-01-01": { ...DailyPayload... },
      "newsletters:scrapes:2024-01-02": { ...DailyPayload... },
      "cache:enabled": true
    }
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    with open(export_file) as f:
        data = json.load(f)

    for key, value in data.items():
        if key.startswith('newsletters:scrapes:'):
            date = key.split(':')[-1]
            payload = value

            # Insert articles
            for article in payload['articles']:
                supabase.table('articles').upsert({
                    'url': article['url'],
                    'title': article['title'],
                    'issue_date': date,
                    'category': article['category'],
                    'source_id': article['sourceId'],
                    'section': article.get('section'),
                    'section_emoji': article.get('sectionEmoji'),
                    'section_order': article.get('sectionOrder'),
                    'newsletter_type': article.get('newsletterType'),
                    'removed': article.get('removed', False),
                    'tldr_hidden': article.get('tldrHidden', False),
                    'is_read': article.get('read', {}).get('isRead', False),
                    'read_marked_at': article.get('read', {}).get('markedAt'),
                    'tldr_status': article.get('tldr', {}).get('status', 'unknown'),
                    'tldr_markdown': article.get('tldr', {}).get('markdown'),
                    'tldr_effort': article.get('tldr', {}).get('effort'),
                    'tldr_checked_at': article.get('tldr', {}).get('checkedAt'),
                    'tldr_error_message': article.get('tldr', {}).get('errorMessage')
                }).execute()

            # Insert issues
            for issue in payload['issues']:
                supabase.table('issues').upsert({
                    'date': date,
                    'source_id': issue['source_id'],
                    'category': issue['category'],
                    'title': issue.get('title'),
                    'subtitle': issue.get('subtitle')
                }).execute()

        elif key == 'cache:enabled':
            supabase.table('user_preferences').upsert({
                'key': 'cache:enabled',
                'value': value
            }).execute()
```

---

## 6. Security Architecture

### Row Level Security (RLS)

**Critical Finding:** RLS is **mandatory** for secure Supabase access. Without RLS, all data is publicly accessible via the anon key.

#### Service Role Key vs. Anon Key

**Service Role Key** (`SUPABASE_SERVICE_KEY`):
- **Bypasses all RLS policies**
- **NEVER expose to client**
- Use in Flask backend only
- Appropriate for server-side operations

**Anon Key** (`SUPABASE_API_KEY`):
- Respects RLS policies
- Safe to expose in client (if implementing client-side access)
- Limited access based on policies

#### RLS Policies for This Project

**Current State:** Single-user application (no authentication)

**Option 1: Permissive (Current Model)**
```sql
-- Allow all operations (matches localStorage behavior)
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations" ON articles
  FOR ALL
  USING (true)
  WITH CHECK (true);
```

**Option 2: API-Only Access (Recommended)**
```sql
-- No direct client access; all operations through Flask backend using service_role key
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;

-- No policies needed; service_role bypasses RLS
-- Client cannot access database directly
```

**Option 3: Future Multi-User Support**
```sql
-- If adding authentication later
CREATE POLICY "Users see their own data" ON articles
  FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users update their own data" ON articles
  FOR UPDATE
  USING (auth.uid() = user_id);
```

**Recommendation:** Start with Option 2 (API-only). Client never accesses Supabase directly; all operations through Flask backend with service_role key.

### Environment Variables

**Backend (Flask):**
```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbG...  # Service role (bypasses RLS)
```

**Client (Future, if needed):**
```bash
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbG...  # Anon key (respects RLS)
```

**Critical:** Use `util.resolve_env_var()` to access all environment variables in Python code.

---

## 7. Real-time Synchronization

### Supabase Realtime Architecture

**How It Works:**
1. PostgreSQL replication captures database changes
2. Realtime server (Elixir) converts changes to JSON
3. Changes broadcast via WebSockets to subscribed clients

### Setup Requirements

**1. Enable Replication for Tables**
```sql
-- Enable realtime for articles table
ALTER PUBLICATION supabase_realtime ADD TABLE articles;

-- Optional: Include "previous" data in updates/deletes
ALTER TABLE articles REPLICA IDENTITY FULL;
```

**2. Python Backend (Async)**
```python
from supabase import acreate_client

# Async client required for realtime
async_supabase = await acreate_client(url, key)

# Subscribe to changes
channel = async_supabase.channel("db-changes")
channel.on_postgres_changes(
    "UPDATE",
    schema="public",
    table="articles",
    callback=lambda payload: print("Article updated:", payload)
)
await channel.subscribe()
```

**3. Client-Side (JavaScript)**
```javascript
// If implementing client-side realtime subscriptions
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

supabase
  .channel('articles-changes')
  .on('postgres_changes',
    { event: 'UPDATE', schema: 'public', table: 'articles' },
    (payload) => {
      console.log('Change received!', payload)
      // Update React state
    }
  )
  .subscribe()
```

### Realtime Use Cases for This Project

**Current localStorage Model:**
- Client-side mutations → Instant UI update → localStorage write
- No network latency
- Changes persist in browser only

**With Realtime Subscriptions:**
- Client mutation → API call → Database update → Realtime notification → UI update
- Adds network latency
- Changes persist server-side

**Recommendation:**

1. **Optimistic Updates**: Update UI immediately on user action
2. **Background Sync**: Send API request to persist change
3. **Realtime Reconciliation**: Subscribe to realtime events to sync changes from other sources (future multi-device support)

```javascript
// Optimistic update pattern
function markAsRead(article) {
  // 1. Update UI immediately (optimistic)
  setLocalState({ ...article, isRead: true })

  // 2. Persist to backend
  fetch('/api/user-state/article', {
    method: 'POST',
    body: JSON.stringify({ url: article.url, isRead: true })
  })
  .catch(error => {
    // 3. Rollback on failure
    setLocalState({ ...article, isRead: false })
    showError('Failed to save')
  })
}
```

**Performance Note:** Realtime adds minimal overhead (~1-2ms) but requires WebSocket connection. Disable if not needed.

---

## 8. Client-Side DOM State Management

### Current Challenge: CSS States and Persistence

From the user's requirements:
> "The most important thing is to think about all the client-DOM (css) states. Including through a session and after page refresh (Cmd+R)."

**Current localStorage Flow:**
1. User clicks article → `markAsRead()` called
2. `useArticleState` updates payload in localStorage
3. Custom event `'local-storage-change'` dispatched
4. All `ArticleCard` components re-render
5. CSS classes applied based on state (`isRead`, `isRemoved`, etc.)
6. On page refresh → localStorage loads → Same CSS state restored

**CSS State Dependencies (from codebase):**

```javascript
// ArticleCard.jsx (inferred from architecture)
const cssClass = computed(() => {
  if (article.removed) return 'article-removed'  // strikethrough, dashed border
  if (article.tldrHidden) return 'article-tldr-hidden'  // deprioritized
  if (article.read?.isRead) return 'article-read'  // muted text
  return 'article-unread'  // bold text
})
```

**Sorting State:**
```javascript
// ArticleList.jsx (from ARCHITECTURE.md)
function sortArticles(articles) {
  return articles.sort((a, b) => {
    const stateA = a.removed ? 3 : a.tldrHidden ? 2 : a.read?.isRead ? 1 : 0
    const stateB = b.removed ? 3 : b.tldrHidden ? 2 : b.read?.isRead ? 1 : 0

    if (stateA !== stateB) return stateA - stateB
    return (a.originalOrder ?? 0) - (b.originalOrder ?? 0)
  })
}
```

### Migration Strategy for DOM States

**Goal:** Preserve exact same visual behavior and state transitions.

**Approach 1: Server-Side State, Client-Side Rendering (Recommended)**

```
User Action
    ↓
Update React State (optimistic)
    ↓
Apply CSS Classes (immediate)
    ↓
API Call to Backend (async)
    ↓
Database Write
    ↓
Response Confirmation
    ↓
(On Error: Rollback React State)
```

**Approach 2: Server-Side Rendering with State**

```
User Action
    ↓
API Call to Backend
    ↓
Database Write
    ↓
Server Renders Updated HTML
    ↓
Send HTML to Client
    ↓
Client Replaces DOM
```

**Problem:** Server-side rendering breaks CSS transitions (research finding: "completely re-creates the DOM elements").

**Recommendation:** Use Approach 1 (Client-Side Rendering) to preserve CSS transitions.

### Implementation Pattern

**1. Maintain Client-Side State Management**

```javascript
// Keep current hooks structure
const { article, markAsRead, setRemoved } = useArticleState(date, url)

// But change storage backend
function useArticleState(date, url) {
  // Instead of localStorage
  const [article, setArticle] = useState(null)

  // Fetch from server on mount
  useEffect(() => {
    fetch(`/api/articles/${date}/${encodeURIComponent(url)}`)
      .then(res => res.json())
      .then(setArticle)
  }, [date, url])

  // Update functions send API requests
  const markAsRead = useCallback(() => {
    // Optimistic update
    setArticle(prev => ({ ...prev, isRead: true, readMarkedAt: new Date().toISOString() }))

    // Persist to backend
    fetch(`/api/articles/${encodeURIComponent(url)}/read`, { method: 'POST' })
      .catch(error => {
        // Rollback on error
        setArticle(prev => ({ ...prev, isRead: false, readMarkedAt: null }))
      })
  }, [url])

  return { article, markAsRead }
}
```

**2. Preserve CSS Class Application**

No changes needed. CSS classes are derived from React state, which remains client-side.

**3. Handle Page Refresh**

```javascript
// On component mount
useEffect(() => {
  // Fetch all articles for date range
  fetch(`/api/articles?start_date=${startDate}&end_date=${endDate}`)
    .then(res => res.json())
    .then(data => {
      // Populate React state
      setArticles(data.articles)
      setIssues(data.issues)
    })
}, [startDate, endDate])
```

**4. Maintain Sorting Logic**

No changes. Sorting happens client-side on React state.

### Performance Optimization

**Current localStorage:**
- Read: ~0.01ms (synchronous)
- Write: ~0.1ms (synchronous)

**With Database:**
- Read: ~50-200ms (network + query)
- Write: ~50-200ms (network + insert)

**Mitigation:**

1. **Aggressive Caching:**
   ```javascript
   // Cache API responses in React state
   const [cache, setCache] = useState(new Map())
   ```

2. **Batch Updates:**
   ```javascript
   // Debounce rapid state changes
   const debouncedSync = useDebouncedCallback(syncToBackend, 500)
   ```

3. **Optimistic UI:**
   Always update UI first, sync to backend in background.

4. **Prefetching:**
   ```javascript
   // Fetch next/prev dates on idle
   useIdleCallback(() => prefetchAdjacentDates())
   ```

---

## 9. Performance Considerations

### Caching Strategy

**PostgreSQL Built-in Caching:**
- `shared_buffers`: In-memory cache for frequently accessed data
- Monitor cache hit ratio: `SELECT * FROM pg_stat_database;`
- Target: >99% cache hit ratio

**Application-Level Caching:**

```python
# In-memory cache for frequently accessed data
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=128)
def get_articles_for_date(date: str):
    return supabase.table('articles') \
        .select('*') \
        .eq('issue_date', date) \
        .execute()

# Invalidate cache on writes
def update_article(url: str, updates: dict):
    result = supabase.table('articles').update(updates).eq('url', url).execute()
    get_articles_for_date.cache_clear()
    return result
```

**Materialized Views for Aggregations:**

```sql
-- Pre-computed daily summaries
CREATE MATERIALIZED VIEW daily_article_stats AS
SELECT
  issue_date,
  COUNT(*) as total_articles,
  COUNT(*) FILTER (WHERE is_read) as read_count,
  COUNT(*) FILTER (WHERE removed) as removed_count
FROM articles
GROUP BY issue_date;

-- Refresh periodically
REFRESH MATERIALIZED VIEW daily_article_stats;
```

### Index Strategy

**Primary Indexes:**
```sql
CREATE INDEX idx_articles_issue_date ON articles(issue_date);
CREATE INDEX idx_articles_source_id ON articles(source_id);
CREATE INDEX idx_articles_category ON articles(category);
```

**Partial Indexes (for filtered queries):**
```sql
-- Only index removed articles (typically small set)
CREATE INDEX idx_articles_removed ON articles(issue_date)
WHERE removed = TRUE;

-- Index articles with TLDRs
CREATE INDEX idx_articles_has_tldr ON articles(url)
WHERE tldr_status = 'available';
```

**Composite Indexes (for common query patterns):**
```sql
-- For fetching date range with filters
CREATE INDEX idx_articles_date_source ON articles(issue_date, source_id);
```

### Query Optimization

**Current API Pattern:**
```python
# Fetch all articles for date range
articles = supabase.table('articles') \
    .select('*') \
    .gte('issue_date', start_date) \
    .lte('issue_date', end_date) \
    .execute()
```

**Optimized Pattern:**
```python
# Only fetch needed fields
articles = supabase.table('articles') \
    .select('url, title, issue_date, category, source_id, removed, is_read, tldr_status') \
    .gte('issue_date', start_date) \
    .lte('issue_date', end_date) \
    .order('issue_date', desc=True) \
    .execute()
```

**Pagination for Large Result Sets:**
```python
# Paginate if >1000 articles
PAGE_SIZE = 100
articles = supabase.table('articles') \
    .select('*') \
    .gte('issue_date', start_date) \
    .lte('issue_date', end_date) \
    .range(0, PAGE_SIZE - 1) \
    .execute()
```

### UNLOGGED Tables for Transient Data

Research finding: UNLOGGED tables provide huge performance gains for cache-like data.

```sql
-- For temporary scrape results (before user confirmation)
CREATE UNLOGGED TABLE scrape_cache (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Trade-off:** UNLOGGED tables are not crash-safe. Acceptable for transient data.

---

## 10. Implementation Requirements

### Database Setup

**1. Create Supabase Project**
- Sign up at supabase.com or use existing project
- Note URL and service_role key

**2. Set Environment Variables**

Add to `.env` (already exists in project):
```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbG...
SUPABASE_API_KEY=eyJhbG...  # anon key (optional)
```

Verify with:
```bash
source ./setup.sh
env | grep SUPABASE
```

**3. Initialize Supabase CLI**

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link to project
supabase link --project-ref xxx

# Initialize migrations directory
supabase init
```

**4. Create Initial Migration**

```bash
# Generate migration file
supabase migration new initial_schema

# Edit supabase/migrations/xxx_initial_schema.sql
# Add schema from Section 4
```

**5. Apply Migration**

```bash
# Test locally
supabase db reset

# Apply to remote
supabase db push
```

### Python Backend Changes

**1. Create Supabase Client Module**

```python
# supabase_client.py
import util
from supabase import create_client

class SupabaseClient:
    _instance = None

    def __init__(self):
        url = util.resolve_env_var("SUPABASE_URL")
        key = util.resolve_env_var("SUPABASE_SERVICE_KEY")
        self.client = create_client(url, key)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance.client

supabase = SupabaseClient.get_instance()
```

**2. Create Data Access Layer**

```python
# db_service.py
from supabase_client import supabase

def get_articles_for_date_range(start_date: str, end_date: str):
    """
    Fetch all articles for date range.
    Returns same structure as localStorage DailyPayload.
    """
    result = supabase.table('articles') \
        .select('*') \
        .gte('issue_date', start_date) \
        .lte('issue_date', end_date) \
        .order('issue_date', desc=True) \
        .execute()

    return result.data

def update_article_state(url: str, updates: dict):
    """Update article user state (read, removed, tldrHidden)."""
    result = supabase.table('articles') \
        .update(updates) \
        .eq('url', url) \
        .execute()

    return result.data

def upsert_article(article: dict):
    """Insert or update article."""
    result = supabase.table('articles') \
        .upsert(article) \
        .execute()

    return result.data
```

**3. Add API Endpoints**

```python
# serve.py
from db_service import get_articles_for_date_range, update_article_state

@app.route("/api/articles", methods=["GET"])
def get_articles():
    """Fetch articles for date range."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    articles = get_articles_for_date_range(start_date, end_date)

    # Group by date (matching localStorage DailyPayload structure)
    payloads = build_daily_payloads_from_articles(articles)

    return jsonify({
        "success": True,
        "payloads": payloads
    })

@app.route("/api/articles/<path:url>/state", methods=["POST"])
def update_article_state_endpoint(url):
    """Update article user state."""
    data = request.get_json()

    # Validate allowed fields
    allowed_updates = {'removed', 'tldr_hidden', 'is_read', 'read_marked_at'}
    updates = {k: v for k, v in data.items() if k in allowed_updates}

    result = update_article_state(url, updates)

    return jsonify({
        "success": True,
        "article": result
    })
```

### Client-Side Changes

**1. Create API Client**

```javascript
// client/src/lib/api.js
export async function fetchArticlesForDateRange(startDate, endDate) {
  const response = await fetch(`/api/articles?start_date=${startDate}&end_date=${endDate}`)
  const data = await response.json()

  if (!data.success) {
    throw new Error('Failed to fetch articles')
  }

  return data.payloads
}

export async function updateArticleState(url, updates) {
  const response = await fetch(`/api/articles/${encodeURIComponent(url)}/state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates)
  })

  const data = await response.json()

  if (!data.success) {
    throw new Error('Failed to update article')
  }

  return data.article
}
```

**2. Update `useArticleState` Hook**

```javascript
// client/src/hooks/useArticleState.js
import { useState, useCallback, useEffect } from 'react'
import { updateArticleState as apiUpdateArticleState } from '../lib/api'

export function useArticleState(date, url) {
  const [article, setArticle] = useState(null)
  const [loading, setLoading] = useState(false)

  // Fetch from parent context (ArticleList provides articles)
  // Or fetch individually if needed

  const updateArticle = useCallback(async (updates) => {
    // Optimistic update
    setArticle(prev => ({ ...prev, ...updates }))

    try {
      // Persist to backend
      await apiUpdateArticleState(url, updates)
    } catch (error) {
      // Rollback on error
      setArticle(prev => ({ ...prev }))  // Revert
      console.error('Failed to update article:', error)
      throw error
    }
  }, [url])

  const markAsRead = useCallback(() => {
    return updateArticle({
      is_read: true,
      read_marked_at: new Date().toISOString()
    })
  }, [updateArticle])

  // ... other methods

  return {
    article,
    loading,
    markAsRead,
    // ... other methods
  }
}
```

### Testing Strategy

**1. Backend Unit Tests**

```python
# test_db_service.py
import pytest
from db_service import get_articles_for_date_range, update_article_state

def test_get_articles_for_date_range():
    articles = get_articles_for_date_range('2024-01-01', '2024-01-03')
    assert len(articles) > 0
    assert all('url' in a for a in articles)

def test_update_article_state():
    result = update_article_state(
        'https://example.com/article',
        {'is_read': True}
    )
    assert result['is_read'] == True
```

**2. Integration Tests**

```python
# test_api_endpoints.py
def test_get_articles_endpoint(client):
    response = client.get('/api/articles?start_date=2024-01-01&end_date=2024-01-03')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
```

**3. E2E Tests (Playwright/Cypress)**

```javascript
test('mark article as read persists after refresh', async ({ page }) => {
  await page.goto('/')

  // Scrape newsletters
  await page.fill('[name=startDate]', '2024-01-01')
  await page.fill('[name=endDate]', '2024-01-01')
  await page.click('button:text("Scrape")')

  // Wait for results
  await page.waitForSelector('.article-card')

  // Click first article
  await page.click('.article-card:first-child .article-title')

  // Verify marked as read
  await expect(page.locator('.article-card:first-child')).toHaveClass(/article-read/)

  // Refresh page
  await page.reload()

  // Verify still marked as read
  await expect(page.locator('.article-card:first-child')).toHaveClass(/article-read/)
})
```

### Rollout Plan

**Week 1: Backend Setup**
- [ ] Create Supabase project
- [ ] Set up migrations
- [ ] Create initial schema
- [ ] Implement `supabase_client.py`
- [ ] Implement `db_service.py`
- [ ] Write unit tests

**Week 2: API Layer**
- [ ] Add API endpoints
- [ ] Implement write-through caching (write to DB during scrapes)
- [ ] Test with existing frontend (no changes)
- [ ] Verify data accumulating in database

**Week 3: Client Migration (Read Path)**
- [ ] Implement API client (`api.js`)
- [ ] Update `useArticleState` to read from API
- [ ] Keep localStorage as fallback
- [ ] Deploy and monitor

**Week 4: Client Migration (Write Path)**
- [ ] Update state mutations to call API
- [ ] Implement optimistic updates
- [ ] Add error handling and rollback
- [ ] Deploy and monitor

**Week 5: Polish & Optimization**
- [ ] Add realtime subscriptions (optional)
- [ ] Implement caching strategies
- [ ] Performance testing
- [ ] Remove localStorage dependencies (optional)

### Monitoring & Observability

**Database Metrics:**
```sql
-- Monitor query performance
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;

-- Monitor cache hit ratio
SELECT
  sum(heap_blks_read) as heap_read,
  sum(heap_blks_hit) as heap_hit,
  sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
FROM pg_statio_user_tables;

-- Monitor table sizes
SELECT
  relname as table_name,
  pg_size_pretty(pg_total_relation_size(relid)) as total_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

**Application Metrics:**
```python
# Add timing to API endpoints
import time
from functools import wraps

def timed(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start
        util.log(f"{f.__name__} took {duration:.3f}s")
        return result
    return wrapper

@timed
def get_articles_for_date_range(start_date, end_date):
    # ...
```

---

## Summary & Key Decisions

### Architecture Decisions

1. **Hybrid Schema:** Normalized core fields + JSONB for optional metadata
2. **Service Role Backend:** All database access through Flask using service_role key
3. **Client-Side Rendering:** Preserve CSS transitions and instant UI updates
4. **Optimistic Updates:** Update UI first, sync to backend asynchronously
5. **Gradual Migration:** Phased rollout with localStorage fallback

### Critical Implementation Points

1. **Preserve State Transitions:** Maintain exact same state machine (0→1→2→3)
2. **CSS Class Application:** Derived from React state, no changes needed
3. **Page Refresh Behavior:** Fetch from API on mount, populate React state
4. **Error Handling:** Rollback optimistic updates on API failure
5. **Performance:** Aggressive caching, batching, prefetching

### Next Steps for Implementation Phase

1. Read `ARCHITECTURE.md` thoroughly to understand current state machine
2. Map each localStorage operation to corresponding database operation
3. Design API endpoints matching current hook interfaces
4. Implement optimistic update pattern for all state mutations
5. Write comprehensive tests for state persistence
6. Plan CSS state validation after migration

### Open Questions for Planning Session

1. **Authentication:** Add user accounts in future? (affects RLS design)
2. **Multi-Device Sync:** Use realtime subscriptions or polling?
3. **Offline Support:** Continue using localStorage for offline mode?
4. **Data Retention:** How long to keep articles in database?
5. **Migration Path:** Provide export/import tool for existing localStorage data?

---

## References

- Supabase Docs: https://supabase.com/docs
- Supabase Python API: https://supabase.com/docs/reference/python/introduction
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- React useSyncExternalStore: https://react.dev/reference/react/useSyncExternalStore
- Project ARCHITECTURE.md (see codebase)
- Project GOTCHAS.md (see codebase)
