---
last-updated: 2025-11-08 17:46, 289da49
---
# Supabase Database Reference Guide

Reference guide for using Supabase Database to migrate TLDRScraper's localStorage-based cache to server-side storage.

**Purpose:** Understanding Supabase capabilities, constraints, and decision points for planning the migration.

---

## Table of Contents

1. [What is Supabase?](#what-is-supabase)
2. [Free Tier Limits & Quotas](#free-tier-limits--quotas)
3. [Python API Overview](#python-api-overview)
4. [Setup Prerequisites](#setup-prerequisites)
5. [Database Design Decision Points](#database-design-decision-points)
6. [Common Gotchas & Pitfalls](#common-gotchas--pitfalls)
7. [Security: RLS Configuration](#security-rls-configuration)
8. [Migration Strategy Considerations](#migration-strategy-considerations)
9. [Useful API Patterns](#useful-api-patterns)

---

## What is Supabase?

Supabase is an open-source Firebase alternative built on PostgreSQL. For this project, the relevant components are:

### Core Stack
- **PostgreSQL Database**: Full Postgres (30+ years stable, open-source)
- **PostgREST**: Auto-generates REST API from your database schema
- **Realtime**: WebSocket server for live database change notifications
- **Row Level Security (RLS)**: Postgres-native per-row access control

### Key Advantages for This Migration
1. **No API boilerplate needed**: PostgREST generates CRUD endpoints automatically
2. **Postgres power**: JSONB, full-text search, materialized views, triggers, functions
3. **Open source**: Can self-host, no vendor lock-in
4. **Python client**: Official `supabase-py` library with similar API to JS client

### What You Get
When you create a Supabase project, you get:
- A dedicated Postgres database
- Auto-generated REST API at `https://[project-id].supabase.co/rest/v1/`
- Auto-generated GraphQL API (optional)
- Dashboard for managing tables, policies, functions
- Connection pooler (PgBouncer)

---

## Free Tier Limits & Quotas

**Critical for Planning:** You're on the free tier. Here are the hard limits:

### Database & Storage
| Resource | Free Tier Limit | Notes |
|----------|----------------|-------|
| Database size | **500 MB** | Per project, all tables combined |
| File storage | 1 GB | Separate from database |
| Max file upload | 50 MB | Per file |

**Planning Implication:** Estimate current localStorage size and project growth. 500 MB is generous for text/metadata but can fill up with large TLDR responses cached over time.

### API & Performance Limits
| Resource | Free Tier Limit | Notes |
|----------|----------------|-------|
| Bandwidth | **10 GB/month** | 5 GB cached + 5 GB uncached |
| API requests | No hard limit | Rate-limited per second |
| Database reads | ~1200/second | Sustained throughput |
| Database writes | ~1000/second | Sustained throughput |
| Monthly Active Users | 50,000 MAU | Authentication related |
| Edge Functions | 500K invocations | Per month |

**Planning Implication:** 10 GB bandwidth is ~10,000 pages of content or ~330 MB/day. Single-user app shouldn't hit this, but if you scrape heavily or cache large volumes, monitor usage.

### Realtime Features
| Resource | Free Tier Limit | Notes |
|----------|----------------|-------|
| Concurrent connections | 200 | WebSocket connections |
| Realtime messages | 2 million/month | Per billing period |
| Max message size | 250 KB | Per realtime message |

**Planning Implication:** If you implement realtime sync between client and server, these limits are generous for a single-user application.

### Project & Operations
| Resource | Free Tier Limit | Notes |
|----------|----------------|-------|
| Active projects | 2 projects | Per organization |
| Inactive project pause | 7 days | Projects auto-pause after inactivity |
| Log retention | 1 day | API & Database logs |
| Query timeout | 8 seconds default, 2 min max | Per statement |

**Planning Implication:** 2 projects means you can have prod + dev/staging OR prod + experimental. Inactive pause means you need to access the project at least weekly to keep it active.

### Monitoring Usage
Check usage in dashboard: `Project Settings > Usage`

Monitor specific metrics:
- Database size: `Dashboard > Database > Usage`
- Bandwidth: `Dashboard > Settings > Usage > Bandwidth`
- API requests: `Dashboard > Settings > Usage > API Requests`

**Pro Tip:** Set up alerts before hitting limits. Supabase will email warnings at 80% usage on paid tiers, but free tier just stops working.

---

## Python API Overview

### Installation

```bash
pip install supabase
# Current version: Nov 6, 2025 release
# Python requirement: >= 3.9
```

Or with uv (already used in this project):
```bash
uv add supabase
```

### Two Client Types: Sync vs Async

**Critical Decision Point:** Choose the right client for your use case.

#### Sync Client (create_client)
```python
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

# Use anywhere in Flask without async/await
articles = supabase.table('articles').select('*').execute()
```

**Use when:**
- Flask backend operations (serve.py, tldr_service.py)
- Any synchronous context
- CRUD operations (no realtime subscriptions)

**Cannot use:**
- Realtime subscriptions (requires async)

#### Async Client (acreate_client)
```python
from supabase import acreate_client

async_supabase = await acreate_client(url, key)

# Must use in async context
articles = await async_supabase.table('articles').select('*').execute()
```

**Use when:**
- Need realtime database subscriptions
- Async web frameworks (FastAPI, aiohttp, etc.)

**Cannot use:**
- Regular Flask routes (Flask is sync by default)
- Synchronous initialization (e.g., during app startup)

**Trade-off:** Realtime is only available with async client, but Flask is sync. If you want realtime, you'll need to either:
1. Run async client in a separate thread/process
2. Switch to FastAPI
3. Use polling instead of realtime subscriptions

**Recommendation for This Project:** Use sync client. Realtime is nice-to-have, but adds complexity. Polling or manual refresh is simpler for single-user app.

---

## Setup Prerequisites

**These steps must be completed IN ORDER before you can use the database programmatically.**

### 1. Create Supabase Project
- Go to `https://supabase.com/dashboard`
- Click "New Project"
- Choose organization, name, password, region
- **Wait 2-3 minutes** for project provisioning

**What you get:** Empty Postgres database, auto-generated API endpoints

### 2. Obtain API Credentials

Navigate to `Project Settings > API`:

**Two keys are available:**
1. **anon (public) key**: `SUPABASE_API_KEY`
   - Safe to expose in client-side code
   - Respects Row Level Security (RLS) policies
   - Use for client-side operations (if you implement direct client access)

2. **service_role key**: `SUPABASE_SERVICE_KEY`
   - **NEVER expose to client**
   - Bypasses ALL RLS policies
   - Full admin access to database
   - Use in Flask backend only

**Also note:** Project URL is at `https://[project-id].supabase.co`

**Environment Variables (Add to your .env):**
```bash
SUPABASE_URL=https://[project-id].supabase.co
SUPABASE_SERVICE_KEY=eyJhbG...  # Service role key
SUPABASE_API_KEY=eyJhbG...      # Anon key (optional)
```

**In Python:**
```python
import util
url = util.resolve_env_var("SUPABASE_URL")
key = util.resolve_env_var("SUPABASE_SERVICE_KEY")
```

### 3. Create Database Schema

**Two Options:**

#### Option A: Dashboard (GUI)
- Go to `Database > Tables`
- Click "Create a new table"
- Define columns, types, constraints
- Click "Save"

**Pros:**
- Visual, beginner-friendly
- See changes immediately
- No SQL knowledge needed

**Cons:**
- Not version controlled
- Hard to replicate across environments
- Tables owned by `supabase_admin` role (can cause permission issues later)

#### Option B: SQL Editor
- Go to `SQL Editor`
- Write `CREATE TABLE` statements
- Run query

**Pros:**
- Version controlled (save SQL files)
- Reproducible
- Tables owned by `postgres` role (better for migrations)

**Cons:**
- Requires SQL knowledge
- No immediate visual feedback

#### Option C: Migrations (CLI) - **Recommended for Production**
```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link to project
supabase link --project-ref [project-id]

# Create migration
supabase migration new initial_schema

# Edit supabase/migrations/[timestamp]_initial_schema.sql
# Add your CREATE TABLE statements

# Apply locally (if running local Supabase)
supabase db reset

# Apply to remote
supabase db push
```

**Pros:**
- Version controlled
- Reproducible across environments
- Can diff changes: `supabase db diff`
- Professional workflow

**Cons:**
- Requires CLI setup
- Steeper learning curve

**Recommendation:** Start with Dashboard (Option A) for prototyping, then export to migrations (Option C) once schema is stable.

**Critical Gotcha:** If you create tables via Dashboard, they're owned by `supabase_admin`. If you later create migrations via CLI, they're owned by `postgres`. This can cause permission errors. Be consistent within a project.

### 4. Enable Row Level Security (RLS)

**THIS IS MANDATORY BEFORE ANY DATA ACCESS WORKS.**

Even on free tier, Supabase enforces security through RLS. Here's what happens:

**Without RLS:**
- Anyone with your `anon` key can read/write all data
- Terrible security, but works for testing

**With RLS enabled but no policies:**
- **ALL ACCESS IS BLOCKED** (including your own API calls)
- You'll get empty results or `403 Forbidden` errors

**With RLS enabled + policies:**
- Access controlled per row based on policies
- Secure, production-ready

**How to enable RLS:**

Via Dashboard:
1. Go to `Database > Tables`
2. Click on table name
3. Click "Enable RLS" in top right

Via SQL:
```sql
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
```

**Then create policies** (see [Security: RLS Configuration](#security-rls-configuration) section below).

### 5. Verify Setup

Test connection with Python:

```python
from supabase import create_client
import os

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

# Test query (replace 'test_table' with your table name)
try:
    result = supabase.table('test_table').select('*').limit(1).execute()
    print("✓ Connection successful:", result.data)
except Exception as e:
    print("✗ Connection failed:", e)
```

**Common errors:**
- `"relation \"test_table\" does not exist"`: Table not created yet
- `"Failed to fetch"`: Wrong SUPABASE_URL
- `"Invalid API key"`: Wrong SUPABASE_SERVICE_KEY
- Empty results but no error: RLS enabled with no policies (using anon key)

---

## Database Design Decision Points

### Decision 1: JSONB vs Normalized Tables

**The Question:** Should I store the article data as JSONB blobs or as normalized columns?

**JSONB Approach:**
```sql
CREATE TABLE daily_cache (
  date DATE PRIMARY KEY,
  payload JSONB  -- Store entire DailyPayload as JSON
);
```

**Normalized Approach:**
```sql
CREATE TABLE articles (
  url TEXT PRIMARY KEY,
  title TEXT,
  issue_date DATE,
  category TEXT,
  -- ... individual columns
);
```

#### When to Use JSONB

**Use JSONB when:**
- Schema is highly variable or unknown upfront
- Data is write-once, read-rarely
- You need to store entire objects without modification
- Fields won't be used in WHERE clauses or JOINs

**Examples:**
- API webhook payloads
- User preferences with dynamic keys
- Audit logs
- Configuration blobs

**For this project:**
- Caching entire scrape responses temporarily
- Storing optional metadata that varies by source

#### When to Use Normalized Tables

**Use normalized tables when:**
- Fields will be queried/filtered frequently
- Data integrity matters (foreign keys, constraints)
- You need efficient indexes on specific fields
- Schema is known and stable

**Examples:**
- Article URL, title, date (queried for filtering)
- User state fields (read, removed, tldrHidden) - used in WHERE clauses
- TLDR status (filtered to find articles needing TLDRs)

**For this project:**
- Core article fields: url, title, issue_date, category
- User state: removed, is_read, tldr_hidden
- TLDR data: status, markdown

#### Performance Comparison

**Research Finding:** PostgreSQL can be **~2000x slower** with JSONB for filtered queries vs indexed columns.

**Why JSONB is slower:**
- No query planner statistics → bad query plans
- GIN indexes less efficient than B-tree for single values
- Must extract JSON values at query time
- Storage overhead (keys duplicated per row, ~2x space)

**Why JSONB can be faster:**
- Avoiding JOINs for complex objects
- Read entire object in one query
- Good for document-style access patterns

#### The Hybrid Approach (Recommended)

**Best Practice:** Use normalized columns for queryable fields + JSONB for truly dynamic data.

```sql
CREATE TABLE articles (
  -- Normalized: frequently queried
  url TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  issue_date DATE NOT NULL,
  category TEXT NOT NULL,
  source_id TEXT NOT NULL,

  -- User state (for filtering/sorting)
  removed BOOLEAN DEFAULT FALSE,
  is_read BOOLEAN DEFAULT FALSE,
  tldr_hidden BOOLEAN DEFAULT FALSE,

  -- JSONB: optional/variable metadata
  metadata JSONB
);
```

**Trade-off Summary:**

| Criterion | JSONB | Normalized | Winner |
|-----------|-------|------------|--------|
| Query performance (filtered) | Slow | Fast | Normalized |
| Schema flexibility | High | Low | JSONB |
| Storage efficiency | Low (2x) | High | Normalized |
| Data integrity | None | Strong (FK, constraints) | Normalized |
| Write performance | Moderate | High | Normalized |
| Read full object | Fast | Slow (JOINs) | JSONB |

**Decision Guide:**
- Will you query/filter by this field? → **Normalized column**
- Is field optional/dynamic? → **JSONB**
- Will field change frequently? → **Normalized** (JSONB rewrites entire value)
- Do you need data integrity? → **Normalized**

### Decision 2: Table Structure for State Management

**The Question:** How should I model the article + user state + TLDR data relationship?

**Option 1: Single Wide Table**
```sql
CREATE TABLE articles (
  url TEXT PRIMARY KEY,
  -- Article fields
  title TEXT,
  issue_date DATE,

  -- User state
  removed BOOLEAN,
  is_read BOOLEAN,
  read_marked_at TIMESTAMPTZ,

  -- TLDR state
  tldr_status TEXT,
  tldr_markdown TEXT,
  tldr_effort TEXT
);
```

**Pros:**
- Simple: one query to get everything
- Matches localStorage structure
- Fast reads (no JOINs)

**Cons:**
- Violates normalization (repeating article data across user states)
- Harder to add multi-user support later
- NULL-heavy if many optional fields

**Use when:**
- Single-user application (this project)
- Performance critical
- Schema unlikely to change

**Option 2: Separate Tables (Normalized)**
```sql
CREATE TABLE articles (
  url TEXT PRIMARY KEY,
  title TEXT,
  issue_date DATE
);

CREATE TABLE user_article_state (
  user_id UUID,
  article_url TEXT REFERENCES articles(url),
  removed BOOLEAN,
  is_read BOOLEAN,
  PRIMARY KEY (user_id, article_url)
);

CREATE TABLE article_tldrs (
  article_url TEXT PRIMARY KEY REFERENCES articles(url),
  status TEXT,
  markdown TEXT
);
```

**Pros:**
- Proper normalization
- Easy to add multi-user support
- Clear separation of concerns

**Cons:**
- Requires JOINs on every query
- More complex queries
- Slower for simple reads

**Use when:**
- Multi-user support planned
- Clear domain boundaries
- Data integrity critical

**Option 3: Hybrid (Recommended)**
```sql
CREATE TABLE articles (
  url TEXT PRIMARY KEY,
  title TEXT,
  issue_date DATE,

  -- Frequently accessed state (denormalized for speed)
  removed BOOLEAN DEFAULT FALSE,
  is_read BOOLEAN DEFAULT FALSE,
  tldr_status TEXT DEFAULT 'unknown',

  -- Large/optional data in separate tables
  -- (Add later if needed)
);

CREATE TABLE article_tldrs (
  article_url TEXT PRIMARY KEY REFERENCES articles(url),
  markdown TEXT,  -- Can be large
  effort TEXT,
  checked_at TIMESTAMPTZ
);
```

**Pros:**
- Fast for common queries (article + state in one table)
- Separates large data (TLDR markdown)
- Balances performance and structure

**Cons:**
- Some denormalization
- Harder to add multi-user later (requires migration)

**Decision Guide:**
- Current: Single-user app → **Option 1 or 3**
- Future: Multi-user planned → **Option 2**
- Performance critical → **Option 1**
- Large text fields (>1KB) → **Option 3** (separate table)

### Decision 3: Caching Strategy

**The Question:** Should I cache entire DailyPayload objects or store articles individually?

**Option A: Cache Full Payloads**
```sql
CREATE TABLE daily_cache (
  date DATE PRIMARY KEY,
  cached_at TIMESTAMPTZ,
  payload JSONB  -- Entire DailyPayload
);
```

**Pros:**
- Exact 1:1 match with localStorage structure
- Fast writes (one upsert per day)
- Fast reads for full day
- Easy migration path

**Cons:**
- Can't query individual articles
- Must load entire day to update one article
- Denormalized

**Use when:**
- You always fetch by date (not by article URL)
- Payload size reasonable (<100KB per day)
- Cache invalidation is all-or-nothing per day

**Option B: Individual Article Rows**
```sql
CREATE TABLE articles (
  url TEXT PRIMARY KEY,
  issue_date DATE,
  -- ... individual fields
);
```

**Pros:**
- Query by URL, date, category, etc.
- Update individual articles
- Normalized

**Cons:**
- Must reconstruct DailyPayload from rows
- More complex queries
- Slower for "get all articles for date"

**Use when:**
- Need to query/update individual articles
- Article-level cache invalidation
- Want to leverage SQL filtering

**Option C: Hybrid (Recommended)**
```sql
-- Normalized storage
CREATE TABLE articles (...);

-- Materialized view for fast daily reads
CREATE MATERIALIZED VIEW daily_payloads AS
SELECT
  issue_date as date,
  json_agg(row_to_json(articles.*)) as articles
FROM articles
GROUP BY issue_date;

-- Refresh when needed
REFRESH MATERIALIZED VIEW daily_payloads;
```

**Pros:**
- Normalized storage (Option B)
- Fast daily reads (Option A)
- Best of both worlds

**Cons:**
- Must refresh materialized view after writes
- Adds complexity

**Decision Guide:**
- Migrate existing localStorage as-is → **Option A**
- Need flexible querying → **Option B**
- High read volume, batch updates → **Option C**

---

## Common Gotchas & Pitfalls

### 2. RLS Blocks Everything by Default

**Problem:** You enable RLS but forget to create policies → all queries return empty results.

**Manifestation:**
```python
# Returns empty list even though data exists
result = supabase.table('articles').select('*').execute()
print(result.data)  # []
```

**Solution:**
1. Check if RLS is enabled: Dashboard → Database → Tables → [table] → "RLS enabled"
2. Check if policies exist: Dashboard → Authentication → Policies
3. If using `service_role` key, RLS is bypassed (make sure you're using correct key)

**Pro Tip:** During development, use `service_role` key in backend to bypass RLS. Add proper policies before deploying to production.

### 3. Dashboard vs CLI Table Ownership

**Problem:** Tables created in Dashboard are owned by `supabase_admin`, tables created via migrations are owned by `postgres`. This causes permission errors when mixing approaches.

**Manifestation:**
```sql
-- Migration fails:
ERROR: must be owner of table articles
```

**Solution:**
Pick one approach and stick with it:
- **Dashboard only**: Fine for small projects
- **Migrations only**: Professional workflow, recommended
- **Mixed**: Transfer ownership: `ALTER TABLE articles OWNER TO postgres;`

**Pro Tip:** Use Dashboard for prototyping, then export schema to migration before committing:
```bash
supabase db diff --schema public > initial_schema.sql
```

### 6. JSONB Query Performance

**Problem:** Filtering on JSONB fields is slow without proper indexes.

**Manifestation:**
```python
# Slow query (seq scan)
articles = supabase.table('articles') \
    .select('*') \
    .contains('metadata', {'tag': 'important'}) \
    .execute()
```

**Solution:**
Create GIN index:
```sql
CREATE INDEX idx_articles_metadata ON articles USING GIN (metadata);
```

**Pro Tip:** Monitor slow queries in Dashboard → Database → Query Performance. Any query >100ms should be investigated.

### 7. Upsert Requires Primary Key

**Problem:** Calling `upsert()` without including the primary key in data.

**Manifestation:**
```python
# Missing 'url' (primary key)
supabase.table('articles').upsert({
    'title': 'New Article',
    'issue_date': '2024-01-01'
}).execute()
# Result: Creates new row every time (no conflict detection)
```

**Solution:**
Always include primary key in upsert data:
```python
supabase.table('articles').upsert({
    'url': 'https://example.com/article',  # Primary key
    'title': 'New Article',
    'issue_date': '2024-01-01'
}).execute()
```

**Pro Tip:** If you have composite primary keys or unique constraints, use `on_conflict` parameter:
```python
.upsert(data, on_conflict='date,source_id')
```

---

## Security: RLS Configuration

### Understanding RLS Flow

**Key Concept:** RLS (Row Level Security) is Postgres-native security. It works like this:

1. User makes query with API key (anon or service_role)
2. Postgres checks: Is RLS enabled on this table?
3. If yes → Apply policies to filter rows
4. If no → Return all rows (insecure!)

**Critical Understanding:** `service_role` key **bypasses ALL RLS policies**. It's like `sudo` for your database.

### Two Key Types

| Key Type | RLS Behavior | Use Case |
|----------|--------------|----------|
| `anon` key | **Respects RLS** | Client-side code, public access |
| `service_role` key | **Bypasses RLS** | Backend server, admin operations |

**For this project:** Flask backend should use `service_role` key. Client (if direct access) uses `anon` key.

### Enable RLS: Step-by-Step

**Step 1: Enable RLS on Table**

Dashboard: Database → Tables → [table] → Enable RLS toggle

SQL:
```sql
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
```

**Step 2: Create Policies**

Without policies, **ALL access is blocked** (even with valid keys).

**Policy Anatomy:**
```sql
CREATE POLICY "policy_name" ON table_name
  FOR operation              -- SELECT, INSERT, UPDATE, DELETE, ALL
  TO role                    -- public, authenticated, service_role
  USING (condition)          -- Boolean expression (for SELECT/UPDATE/DELETE)
  WITH CHECK (condition);    -- Boolean expression (for INSERT/UPDATE)
```

**USING vs WITH CHECK:**
- `USING`: Filters which rows are visible
- `WITH CHECK`: Validates new/modified rows

### Common Policy Patterns

#### Pattern 1: Permissive (Development)

Allow all operations (equivalent to no RLS):

```sql
CREATE POLICY "allow_all" ON articles
  FOR ALL
  USING (true)
  WITH CHECK (true);
```

**Use when:**
- Single-user app
- Development/testing
- Backend uses `service_role` key

**Security:** Low (anyone with anon key has full access)

#### Pattern 2: API-Only Access (Recommended)

Enable RLS but don't create policies. All access goes through backend with `service_role` key:

```sql
-- Just enable RLS, no policies needed
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
```

Backend:
```python
# service_role key bypasses RLS
supabase = create_client(url, SUPABASE_SERVICE_KEY)
```

**Use when:**
- Client never accesses database directly
- All operations through Flask API
- Single source of truth (backend)

**Security:** High (database inaccessible except through your API)

#### Pattern 3: User-Owned Data (Multi-User)

Each user can only see/edit their own data:

```sql
-- Assumes articles have user_id column
CREATE POLICY "users_own_data" ON articles
  FOR ALL
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
```

**Use when:**
- Multi-user application
- Client accesses database directly with `anon` key
- User authentication via Supabase Auth

**Security:** High (per-user data isolation)

### Helper Functions in Policies

Supabase provides helper functions for policies:

| Function | Returns | Use Case |
|----------|---------|----------|
| `auth.uid()` | UUID | Current user ID (from JWT) |
| `auth.jwt()` | JSONB | Full JWT payload |
| `auth.email()` | TEXT | User's email |

**Example:**
```sql
-- Only allow users with admin role
CREATE POLICY "admin_only" ON articles
  FOR ALL
  TO authenticated
  USING (auth.jwt()->>'role' = 'admin');
```

### Policy Debugging

**Problem:** Policy blocks your queries but you don't know why.

**Solution:** Check policy logic in Dashboard → SQL Editor:

```sql
-- Test policy USING clause manually
SELECT * FROM articles
WHERE auth.uid() = user_id;  -- Paste your USING condition

-- Check what auth.uid() returns
SELECT auth.uid();

-- Check JWT payload
SELECT auth.jwt();
```

**Pro Tip:** Policies are just SQL conditions. Test them as regular WHERE clauses to debug.

### RLS Performance Considerations

**Important:** Complex policies can slow down queries.

**Bad policy (slow):**
```sql
-- Multiple JOINs in policy
USING (
  EXISTS (
    SELECT 1 FROM teams
    JOIN team_members ON teams.id = team_members.team_id
    WHERE team_members.user_id = auth.uid()
      AND teams.id = articles.team_id
  )
)
```

**Better policy:**
```sql
-- Materialized permissions table
CREATE TABLE user_permissions (
  user_id UUID,
  article_url TEXT,
  can_access BOOLEAN
);

USING (
  EXISTS (
    SELECT 1 FROM user_permissions
    WHERE user_id = auth.uid()
      AND article_url = articles.url
      AND can_access = true
  )
)
```

**Pro Tip:** Wrap policy functions in `SECURITY DEFINER` functions to cache results per statement:

```sql
CREATE FUNCTION current_user_id() RETURNS UUID AS $$
  SELECT auth.uid()
$$ LANGUAGE SQL SECURITY DEFINER;

-- Policy uses cached function
USING (current_user_id() = user_id)
```

### RLS Checklist for Production

Before deploying:

- [ ] RLS enabled on all tables with user data
- [ ] Policies created for all operations (SELECT, INSERT, UPDATE, DELETE)
- [ ] Policies tested with both `anon` and `authenticated` roles
- [ ] No tables with sensitive data have `USING (true)` policies
- [ ] Backend uses `service_role` key, client uses `anon` key
- [ ] Policy performance tested (check query plans)

---

## Migration Strategy Considerations

### Current State: localStorage Architecture

**What's in localStorage now:**
- Key pattern: `newsletters:scrapes:{date}` → `DailyPayload`
- Structure: `{ date, cachedAt, articles[], issues[] }`
- Article structure: URL as ID, nested read/removed/tldr state
- Total size: Unknown (check browser DevTools → Application → Local Storage)

**Key characteristics:**
- Synchronous read/write
- Zero latency
- Device-specific (not synced)
- Persistent until cleared

### Migration Decision Points

#### Decision: Direct Client Access or API-Only?

**Option A: API-Only (Client → Flask → Supabase)**

```
[React Client]
    ↓ HTTP
[Flask Backend] (service_role key)
    ↓
[Supabase DB]
```

**Pros:**
- Single source of truth (backend)
- Backend can validate/transform data
- RLS not needed (service_role bypasses)
- Existing Flask API just needs new endpoints

**Cons:**
- Extra hop (latency)
- Backend must be always available
- More server load

**Use when:**
- You want backend control/validation
- Already have Flask backend (you do)
- Single-user or simple auth

**Option B: Direct Client Access (Client → Supabase)**

```
[React Client] (anon key)
    ↓
[Supabase DB]
```

**Pros:**
- No backend hop (faster)
- Offline-capable (with local cache)
- Backend only needed for scraping

**Cons:**
- Must configure RLS policies
- Client has database access (security considerations)
- Harder to add business logic

**Use when:**
- Low latency critical
- Want offline support
- Multi-user with proper auth

**Recommendation for This Project:** **Option A (API-Only)**. You already have Flask backend, and single-user app doesn't benefit from direct access complexity.

#### Decision: Full Migration or Hybrid?

**Option A: Full Migration (Remove localStorage)**

- Client reads from API on page load
- All state changes go through API
- localStorage removed entirely

**Pros:**
- Single source of truth
- No sync issues
- Simpler client code

**Cons:**
- Requires network for all operations
- Slower (network latency)
- Must handle offline gracefully

**Option B: Hybrid (localStorage + Supabase)**

- Supabase is source of truth
- localStorage is local cache
- Sync on page load, periodically, or on change

**Pros:**
- Fast reads (localStorage)
- Works offline
- Graceful degradation

**Cons:**
- Sync complexity
- Potential conflicts
- More client code

**Option C: Phased Migration**

Week 1: Backend writes to both localStorage and Supabase
Week 2: Client reads from Supabase, falls back to localStorage
Week 3: Client writes to Supabase
Week 4: Remove localStorage

**Pros:**
- Low risk
- Easy rollback
- Learn as you go

**Cons:**
- Takes longer
- Maintains both systems temporarily

**Decision Guide:**
- Need offline support? → **Option B**
- Want simplicity? → **Option A**
- Risk-averse? → **Option C**

#### Decision: Data Shape in Database

**Question:** Should database schema match localStorage structure exactly?

**Option A: 1:1 Match (Store as JSONB)**

```sql
CREATE TABLE daily_cache (
  date DATE PRIMARY KEY,
  payload JSONB  -- Exact DailyPayload from localStorage
);
```

**Pros:**
- Trivial migration (just copy JSON)
- No schema changes needed
- Easy to revert

**Cons:**
- Can't query articles individually
- No data integrity
- Poor performance for filters

**Option B: Normalized Schema**

```sql
CREATE TABLE articles (...);
CREATE TABLE issues (...);
-- Reconstruct DailyPayload on read
```

**Pros:**
- Proper database design
- Queryable
- Better performance

**Cons:**
- Must transform data on read/write
- More complex queries
- Harder to match localStorage exactly

**Recommendation:** Start with Option A for rapid migration, refactor to Option B once working.

### Preserving Client-Side DOM States

**Critical Requirement:** CSS classes and sorting depend on article state (read/removed/tldrHidden).

**Current flow:**
1. User clicks article
2. `useArticleState` updates localStorage
3. Custom event `'local-storage-change'` fires
4. Components re-render with new CSS classes
5. On refresh: localStorage → React state → CSS classes

**With Supabase:**
1. User clicks article
2. Optimistic update: React state changes (instant CSS)
3. API call to persist
4. On success: do nothing
5. On failure: rollback React state
6. On refresh: API call → React state → CSS classes

**Key insight:** React state is still source of truth for DOM. Supabase is just persistence layer.

**Implementation pattern:**
```javascript
const [article, setArticle] = useState(null)

function markAsRead() {
  // 1. Optimistic update (instant CSS)
  setArticle(prev => ({ ...prev, isRead: true }))

  // 2. Persist to backend
  fetch('/api/articles/.../mark-read', { method: 'POST' })
    .catch(error => {
      // 3. Rollback on error
      setArticle(prev => ({ ...prev, isRead: false }))
      showErrorToast('Failed to save')
    })
}
```

**This preserves:**
- Zero perceived latency (like localStorage)
- CSS transitions (no DOM replacement)
- State on refresh (via API fetch on mount)

---

## Useful API Patterns

### Pattern 1: Insert vs Upsert vs Update

**When to use each:**

#### Insert
```python
supabase.table('articles').insert({
    'url': 'https://example.com/article',
    'title': 'Article Title'
}).execute()
```

**Use when:**
- Record definitely doesn't exist
- Want error if duplicate found
- Bulk inserting new data

**Fails if:** Primary key or unique constraint violated

#### Upsert
```python
supabase.table('articles').upsert({
    'url': 'https://example.com/article',  # Primary key required
    'title': 'Updated Title'
}).execute()
```

**Use when:**
- Record might exist (idempotent operation)
- Want to create-or-update in one call
- Don't care if new or existing

**Behavior:** If URL exists, updates. Otherwise, inserts.

**Critical:** Primary key (or unique constraint field) MUST be in data.

#### Update
```python
supabase.table('articles') \
    .update({'title': 'New Title'}) \
    .eq('url', 'https://example.com/article') \
    .execute()
```

**Use when:**
- Record definitely exists
- Only updating subset of fields
- Need to filter which rows to update

**Requires:** Filter (`.eq()`, `.in_()`, etc.)

**Decision Guide:**
- New scrape data → **Insert** (URLs are unique per scrape)
- User state changes → **Upsert** (might not have state row yet)
- Specific field update → **Update** (e.g., tldr_status)

### Pattern 2: Querying with Filters

**Basic query:**
```python
# Get all articles
result = supabase.table('articles').select('*').execute()
articles = result.data
```

**With filters:**
```python
# Get articles for specific date
result = supabase.table('articles') \
    .select('*') \
    .eq('issue_date', '2024-01-01') \
    .execute()

# Get articles in date range
result = supabase.table('articles') \
    .select('*') \
    .gte('issue_date', '2024-01-01') \
    .lte('issue_date', '2024-01-31') \
    .execute()

# Multiple conditions (AND)
result = supabase.table('articles') \
    .select('*') \
    .eq('issue_date', '2024-01-01') \
    .eq('removed', False) \
    .execute()

# OR conditions
result = supabase.table('articles') \
    .select('*') \
    .or_('removed.eq.true,is_read.eq.true') \
    .execute()
```

**Common filters:**
| Filter | SQL Equivalent | Example |
|--------|----------------|---------|
| `.eq(col, val)` | `=` | `.eq('status', 'available')` |
| `.neq(col, val)` | `!=` | `.neq('removed', true)` |
| `.gt(col, val)` | `>` | `.gt('issue_date', '2024-01-01')` |
| `.gte(col, val)` | `>=` | `.gte('issue_date', '2024-01-01')` |
| `.lt(col, val)` | `<` | `.lt('issue_date', '2024-02-01')` |
| `.lte(col, val)` | `<=` | `.lte('issue_date', '2024-02-01')` |
| `.in_(col, list)` | `IN` | `.in_('category', ['Tech', 'AI'])` |
| `.is_(col, val)` | `IS` | `.is_('removed', null)` |

### Pattern 3: Ordering and Limiting

```python
# Order by date descending
result = supabase.table('articles') \
    .select('*') \
    .order('issue_date', desc=True) \
    .execute()

# Limit results
result = supabase.table('articles') \
    .select('*') \
    .limit(100) \
    .execute()

# Pagination
PAGE_SIZE = 20
result = supabase.table('articles') \
    .select('*') \
    .range(0, PAGE_SIZE - 1) \
    .execute()
```

### Pattern 4: Batch Operations

**Insert multiple:**
```python
articles = [
    {'url': 'https://example.com/1', 'title': 'Article 1'},
    {'url': 'https://example.com/2', 'title': 'Article 2'},
    # ...
]
result = supabase.table('articles').insert(articles).execute()
```

**Upsert multiple:**
```python
result = supabase.table('articles').upsert(articles).execute()
```

**Best Practice:** Batch size 100-1000 rows for optimal performance. Free tier handles ~1000 inserts/second.

### Pattern 5: Error Handling

```python
try:
    result = supabase.table('articles') \
        .insert(article) \
        .execute()

    if result.data:
        print("Success:", result.data)
    else:
        print("No data returned")

except Exception as e:
    print("Error:", str(e))
    # Check error type
    if "duplicate key" in str(e):
        # Handle duplicate
        pass
    elif "violates foreign key" in str(e):
        # Handle FK violation
        pass
```

**Common errors:**
- `"duplicate key value violates unique constraint"`: Primary key or unique constraint violated
- `"violates foreign key constraint"`: Referenced row doesn't exist
- `"violates check constraint"`: Check constraint failed (e.g., invalid enum value)
- `"column \"xyz\" does not exist"`: Typo in column name
- `"permission denied for table xyz"`: RLS blocking access

### Pattern 6: Counting Rows

```python
# Count all articles
result = supabase.table('articles') \
    .select('*', count='exact') \
    .execute()
total = result.count

# Count with filter
result = supabase.table('articles') \
    .select('*', count='exact') \
    .eq('removed', False) \
    .execute()
non_removed_count = result.count
```

**Pro Tip:** For large tables, `count='exact'` can be slow. Use `count='estimated'` for approximate count (much faster).

### Pattern 7: Aggregations

**Sum, avg, min, max:**
```python
# Raw SQL for aggregations (PostgREST doesn't support aggregate functions directly)
result = supabase.rpc('get_article_stats', {}).execute()

# Where get_article_stats is a database function:
# CREATE FUNCTION get_article_stats()
# RETURNS TABLE(total bigint, read_count bigint, removed_count bigint) AS $$
#   SELECT
#     COUNT(*),
#     COUNT(*) FILTER (WHERE is_read),
#     COUNT(*) FILTER (WHERE removed)
#   FROM articles;
# $$ LANGUAGE SQL;
```

**Pro Tip:** For complex aggregations, create database functions and call them via `.rpc()`.

---

## Pro Tips for This Migration

### 1. Start with Write-Through Caching

**Strategy:** Backend writes to both localStorage (via API response) and Supabase. Client continues using localStorage.

**Why:** De-risks migration. Supabase accumulates data in background while localStorage continues working.

**Implementation:**
```python
# In tldr_service.py after scraping
articles = scrape_newsletters(...)

# NEW: Write to Supabase
for article in articles:
    supabase.table('articles').upsert(article).execute()

# EXISTING: Return to client (who writes to localStorage)
return articles
```

**Benefit:** Supabase starts accumulating data immediately. Test queries, schema, performance with real data before touching client.

### 2. Use Database Functions for Complex Logic

**Instead of:**
```python
# Complex logic in Python
articles = supabase.table('articles').select('*').eq('issue_date', date).execute()
# ... process in Python ...
```

**Use database function:**
```sql
CREATE FUNCTION get_daily_payload(p_date DATE)
RETURNS JSONB AS $$
  SELECT json_build_object(
    'date', p_date,
    'articles', json_agg(row_to_json(articles.*)),
    'cachedAt', NOW()
  )
  FROM articles
  WHERE issue_date = p_date;
$$ LANGUAGE SQL;
```

```python
result = supabase.rpc('get_daily_payload', {'p_date': date}).execute()
payload = result.data
```

**Benefits:**
- Less data transferred over network
- Postgres does heavy lifting
- Consistent format (defined in SQL)

### 3. Monitor Query Performance Early

Dashboard → Database → Query Performance shows slow queries.

**Watch for:**
- Queries >100ms
- Full table scans (seq scan)
- Missing indexes

**Fix:** Add indexes to frequently filtered columns:
```sql
CREATE INDEX idx_articles_issue_date ON articles(issue_date);
```

### 4. Test with Production-Scale Data

**Don't:**
- Test with 10 articles
- Assume performance scales

**Do:**
- Insert realistic data volume (e.g., 10,000 articles)
- Test queries at scale
- Measure response times

**How:**
```python
# Generate test data
import random
from datetime import datetime, timedelta

articles = []
for i in range(10000):
    date = datetime.now() - timedelta(days=random.randint(0, 365))
    articles.append({
        'url': f'https://example.com/article-{i}',
        'title': f'Article {i}',
        'issue_date': date.strftime('%Y-%m-%d'),
        'category': random.choice(['Tech', 'AI', 'News']),
        'source_id': random.choice(['tldr_tech', 'tldr_ai', 'hackernews'])
    })

# Batch insert
for i in range(0, len(articles), 100):
    batch = articles[i:i+100]
    supabase.table('articles').insert(batch).execute()
```

### 5. Use Transactions for Multi-Table Inserts

**Problem:** Inserting into multiple tables (articles + issues) can partially fail.

**Solution:** Use Postgres transactions via database function:

```sql
CREATE FUNCTION insert_daily_data(
  p_articles JSONB,
  p_issues JSONB
) RETURNS void AS $$
BEGIN
  -- Insert articles
  INSERT INTO articles (url, title, issue_date, ...)
  SELECT * FROM jsonb_to_recordset(p_articles) AS x(...);

  -- Insert issues
  INSERT INTO issues (date, source_id, category, ...)
  SELECT * FROM jsonb_to_recordset(p_issues) AS y(...);
END;
$$ LANGUAGE plpgsql;
```

```python
result = supabase.rpc('insert_daily_data', {
    'p_articles': articles_json,
    'p_issues': issues_json
}).execute()
```

**Benefit:** All-or-nothing. No partial state.

### 6. Set Up Monitoring Before Migration

**What to monitor:**
- Database size: Dashboard → Database → Usage
- Bandwidth: Dashboard → Settings → Usage
- Query performance: Dashboard → Database → Query Performance
- API response times: Backend logging

**Set alerts:**
- Database size approaching 400 MB (80% of 500 MB free tier limit)
- Bandwidth approaching 8 GB (80% of 10 GB)
- Query response time >500ms

**Log query times:**
```python
import time

def timed_query(table, operation):
    start = time.time()
    result = operation(supabase.table(table))
    duration = time.time() - start

    if duration > 0.1:  # >100ms
        util.log(f"Slow query on {table}: {duration:.2f}s")

    return result

# Usage
result = timed_query('articles', lambda t: t.select('*').eq('issue_date', date).execute())
```

---

## Summary: Key Takeaways

### Critical Requirements
1. **Free tier limits:** 500 MB database, 10 GB bandwidth/month
2. **RLS must be configured:** Enable RLS + create policies OR use service_role key in backend
3. **Async client for realtime:** Regular client doesn't support subscriptions
4. **Upsert needs primary key:** Always include PK in upsert data

### Recommended Decisions for This Project
1. **Use sync client** in Flask backend (no realtime needed)
2. **API-only architecture** (Client → Flask → Supabase with service_role key)
3. **Start with hybrid schema:** Normalized core fields + JSONB for metadata
4. **Phased migration:** Write-through → Hybrid → Full
5. **Use migrations** for schema (via CLI, not Dashboard)

### Must-Do Before Starting
- [ ] Create Supabase project
- [ ] Save SUPABASE_URL and SUPABASE_SERVICE_KEY to .env
- [ ] Verify `util.resolve_env_var()` can read them
- [ ] Test connection with simple query
- [ ] Decide: JSONB vs normalized for article data
- [ ] Enable RLS + create policies OR plan to use service_role only

### Gotchas to Avoid
- Don't mix Dashboard table creation with migrations
- Don't enable RLS without creating policies (blocks all access)
- Don't use pooled connection (port 6543) with asyncpg directly
- Don't forget to include PK in upsert operations
- Don't ignore free tier limits (monitor usage)

---

## Additional Resources

- **Supabase Docs:** https://supabase.com/docs
- **Python API Reference:** https://supabase.com/docs/reference/python/introduction
- **PostgreSQL Docs:** https://www.postgresql.org/docs/current/
- **Free Tier Limits:** https://supabase.com/pricing (scroll to Free tier)
- **RLS Guide:** https://supabase.com/docs/guides/database/postgres/row-level-security
- **Migration Guide:** https://supabase.com/docs/guides/deployment/database-migrations

**Community:**
- Supabase Discord: https://discord.supabase.com
- GitHub Discussions: https://github.com/orgs/supabase/discussions
