---
last_updated: 2026-04-01 18:17, 4018449
description: Multi-article AI synthesis (Digest) with selection integration and dedicated persistence.
---
# Article Digest

## Feature Summary
Implemented a batch synthesis feature that allows users to select multiple articles (via the long-press selection system) and generate a single AI-powered digest.

## Implementation Details
- **Backend**: New `/api/digest` endpoint in `serve.py` that orchestrates parallel content fetching and LLM synthesis.
- **Frontend**: 
  - `DigestButton`: Action trigger visible in select mode.
  - `useDigest`: Singleton hook for managing digest lifecycle (fetch, cache, zen lock).
  - `DigestOverlay`: Dedicated Zen-style overlay for reading digests with gesture support.
- **Persistence**: Dedicated `digests` table in Supabase, keyed by a stable hash of article URLs and effort level.

## Key Primitives
- `generate_digest(articles, effort)`: Service-layer orchestration.
- `get_digest` / `set_digest`: Storage service CRUD for the `digests` table.
- Selection integration: First consumer of the `InteractionContext` selection state.
