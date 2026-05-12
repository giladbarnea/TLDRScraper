---
name: server/storage
description: Server-side database schema and storage flow.
last_updated: 2026-05-12 08:22
---
# Server: Storage

[→ Client: Storage](../client/storage.md) | [→ State Machines: Feed & Storage](../state-machines/feed-and-storage.md)

## Database Schema (Supabase PostgreSQL)

### Table: settings

```sql
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Example row:
{ key: 'ui:theme', value: 'dark', updated_at: '2024-01-01T12:00:00Z' }
```

### Table: daily_cache

```sql
CREATE TABLE daily_cache (
  date DATE PRIMARY KEY,
  payload JSONB NOT NULL,
  cached_at TIMESTAMPTZ DEFAULT NOW()
);

-- Example row:
{
  date: '2024-01-01',
  payload: {
    date: '2024-01-01',
    articles: [{url, title, read, removed, summary, ...}, ...],
    issues: [{date, source_id, category, ...}, ...]
  },
  cached_at: '2024-01-01T12:00:00Z'
}
```

### Table: podcast_episodes

```sql
CREATE TABLE podcast_episodes (
  canonical_url TEXT PRIMARY KEY,
  audio_base64  TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`canonical_url` is a legacy column name from the single-source v0. For multi-source podcasts it stores the stable source-set cache key produced after canonicalizing the selected URLs.

### Storage Flow

1. **Initial Scrape**: API response → Build payloads → POST /api/storage/daily/{date} → Supabase upsert
2. **Cache Hit**: POST /api/storage/daily-range → Read from Supabase → Skip scrape API call
3. **User Interaction**: Modify article state → POST /api/storage/daily/{date} → Supabase upsert → Dispatches 'supabase-storage-change' event
4. **Summary**: Fetch from API → Update article → POST /api/storage/daily/{date} → Supabase upsert
5. **Podcast**: Current `/api/podcast` is temporarily short-circuited to return a local MP3 fixture for client-player testing. Intended generation path remains selected URLs → canonicalize + source-set cache lookup → scrape missing source set → generate MP3 → upsert `podcast_episodes`.
6. **cached_at contract**: Only scrape writes advance cached_at; user-state updates must not mutate cached_at so it remains a scrape freshness signal.

###
