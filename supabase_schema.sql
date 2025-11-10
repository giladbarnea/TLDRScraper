-- TLDRScraper Supabase Database Schema
-- Run this SQL in Supabase Dashboard > SQL Editor

-- Daily newsletter cache (stores DailyPayload JSONB)
CREATE TABLE IF NOT EXISTS daily_cache (
  date DATE PRIMARY KEY,
  payload JSONB NOT NULL,
  cached_at TIMESTAMPTZ DEFAULT NOW()
);

-- Application settings (stores cache:enabled, etc.)
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_daily_cache_date ON daily_cache(date DESC);
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);

-- Enable RLS (service_role key bypasses RLS)
ALTER TABLE daily_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- Verification test inserts
INSERT INTO settings (key, value)
VALUES ('cache:enabled', 'true'::jsonb)
ON CONFLICT (key) DO NOTHING;

INSERT INTO daily_cache (date, payload)
VALUES ('2025-11-09', '{"date":"2025-11-09","articles":[],"issues":[],"cachedAt":"2025-11-09T00:00:00Z"}'::jsonb)
ON CONFLICT (date) DO NOTHING;

-- Test queries
SELECT 'Settings test:' as test, * FROM settings WHERE key = 'cache:enabled';
SELECT 'Daily cache test:' as test, * FROM daily_cache WHERE date = '2025-11-09';
