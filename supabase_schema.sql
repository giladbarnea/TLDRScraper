-- TLDRScraper Database Schema for Supabase
-- Run this in Supabase Dashboard → SQL Editor

-- Table 1: Daily newsletter cache (stores DailyPayload as JSONB)
CREATE TABLE daily_cache (
  date DATE PRIMARY KEY,
  payload JSONB NOT NULL,
  cached_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 2: Application settings (stores cache:enabled, etc.)
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_daily_cache_date ON daily_cache(date DESC);
CREATE INDEX idx_settings_key ON settings(key);

-- Enable RLS (service_role key bypasses RLS, so no policies needed)
ALTER TABLE daily_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- Test queries (optional - uncomment to test)
-- INSERT INTO settings (key, value) VALUES ('cache:enabled', 'true');
-- INSERT INTO daily_cache (date, payload) VALUES
--   ('2025-11-09', '{"date":"2025-11-09","articles":[],"issues":[]}');
-- SELECT * FROM settings WHERE key = 'cache:enabled';
-- SELECT * FROM daily_cache WHERE date = '2025-11-09';
