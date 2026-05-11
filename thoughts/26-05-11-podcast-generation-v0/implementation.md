---
last_updated: 2026-05-11 16:15
plan: ./podcast-creator-readme.md
---

# Podcast Generation v0 — Implementation Notes

## Scope landed
POC + barely-MVP for `POST /api/podcast`: URL → canonicalize → Supabase cache lookup → on miss, scrape + generate + persist → return raw `audio/mpeg`. Surface area is intentionally tiny: one service module (`podcast_service.py`), two storage functions added to `storage_service.py`, one route in `serve.py`, one SQL file under `db/`.

## Key decisions

**Episode profile.** Picked `solo_expert` from podcast-creator's bundled profiles because it's the only one that runs on OpenAI TTS end-to-end. The other profiles default to ElevenLabs, which we don't have a key for. Single-speaker also gives the shortest, cheapest first-run.

**Provider overrides.** All bundled profiles set `transcript_provider="anthropic"` and we have no `ANTHROPIC_API_KEY`. `podcast_service._generate_audio_bytes` overrides both `outline_provider` and `transcript_provider` to OpenAI `gpt-4o-mini`. That's the smallest deviation from the bundled defaults that still runs in this environment.

**Audio storage shape.** `podcast_episodes.audio_base64 TEXT` rather than `bytea`. supabase-py round-trips TEXT verbatim; `bytea` comes back as a `\xhex` string from PostgREST and would require extra decoding on every read. The base64 overhead (~33%) is acceptable at this scale — a ~10 minute mp3 is ~5 MB raw, ~6.6 MB encoded.

**Cache key.** `canonical_url` is the primary key, computed by the existing `util.canonicalize_url`. Reusing the project's canonicalizer means a podcast cached for `lemire.me/...` is found regardless of `www.`, trailing slash, scheme, or fragment — and stays consistent with how `daily_cache`, `digests`, and `seen_urls` key their rows elsewhere.

**Response shape.** Endpoint returns raw mp3 bytes with `Content-Type: audio/mpeg`, plus `X-Cache: hit|miss` and `X-Canonical-Url` headers. JSON+base64 was rejected — clients can pipe straight into `<audio>` or `afplay` without a wrapper.

**Sync/async bridge.** Flask is sync; `podcast_creator.create_podcast` is async. The service entrypoint stays sync and bridges with `asyncio.run` inside the private helper so callers (the route, future cron jobs) don't have to think about it.

## Challenges

**Supabase pooler region guessing.** First DDL attempt against `aws-0-us-west-1.pooler.supabase.com` returned `Tenant or user not found`. Switched to direct `db.<ref>.supabase.co:5432`, which doesn't need the region. Recorded in case someone else hits this; using `pscql` would have masked it.

**Verifying the cache-miss path without burning API credits.** A fresh end-to-end run costs ~6 minutes and a few dollars. Verified the miss → persist → re-hit round-trip by monkey-patching `podcast_service._generate_audio_bytes` and `summarizer.url_to_markdown` against a throwaway URL, then asserting `cached=False` on first call and `cached=True` (with the generator never invoked) on second. Cheap and tight.

**`num_segments` override seemed to be ignored.** Passed `num_segments=2` in the POC; podcast-creator generated 3. Not investigated — barely-MVP doesn't depend on it. Worth checking before any future "shorter podcast" feature.

## Drift from plan

There was no formal plan — the upstream `podcast-creator` README (linked as `plan:` above) was the only document on hand. Everything in this doc is therefore a forward-looking record of intent rather than a delta against a prior design.

## Not done, deliberately

No frontend hook. No durable storage for the generated transcript/outline (only the mp3 lands in Supabase). No auth on the endpoint. No background job for slow generation — the request blocks for several minutes on a cache miss, which is fine for dogfooding from a terminal but unsuitable for the UI. The `solo_expert` profile is hard-coded inside `podcast_service`; profile selection is the obvious next knob to expose.
