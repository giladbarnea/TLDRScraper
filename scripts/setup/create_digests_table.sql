-- Digest cache table. digest_id is a SHA-256 of sorted canonical URLs + effort level.
-- Apply once via the Supabase SQL editor or psql.
CREATE TABLE IF NOT EXISTS digests (
    digest_id    TEXT        PRIMARY KEY,
    markdown     TEXT        NOT NULL,
    included_urls JSONB      NOT NULL,
    article_count INTEGER    NOT NULL,
    effort       TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
