---
last_updated: 2026-04-03 16:22
---
# Digest Feature Architecture

## Overview

The Digest feature lets a user select multiple feed articles and generate a single synthesized AI digest. It spans client selection state, client overlay/state persistence, backend orchestration, content extraction, Gemini generation, and server-side digest caching.

---

## Architecture Diagram (Space)

> Focus: Structural boundaries and major relationships for the Digest domain.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  USER BROWSER                                                           │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ React Client                                                      │  │
│  │                                                                   │  │
│  │  Selection System                                                 │  │
│  │   InteractionContext / selectedIds                                │  │
│  │            │                                                      │  │
│  │            ▼                                                      │  │
│  │   SelectionActionDock.digest ─────► useDigest hook               │  │
│  │                                (request + persistence + zen lock) │  │
│  │                                            │                      │  │
│  │                                            ▼                      │  │
│  │                                       DigestOverlay               │  │
│  │                             (portal + gestures + markdown html)   │  │
│  └───────────────────────────────────────┬───────────────────────────┘  │
└──────────────────────────────────────────│───────────────────────────────┘
                                           │ HTTP
                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Flask Backend                                                          │
│                                                                         │
│  serve.py (/api/digest)                                                │
│          │                                                              │
│          ▼                                                              │
│  tldr_app.generate_digest                                               │
│          │                                                              │
│          ▼                                                              │
│  tldr_service.generate_digest                                           │
│   ├─ parallel url_to_markdown()                                         │
│   ├─ build digest prompt                                                │
│   ├─ call Gemini                                                        │
│   └─ cache get/set via storage_service                                 │
└───────────────────────────────────────┬─────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ External Systems                                                        │
│  - Article sources (scrape via existing summarizer pipeline)           │
│  - Gemini API (generateContent)                                        │
│  - Supabase PostgreSQL (digests table)                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Sequence Diagram (Time)

> Focus: Runtime order from selection to visible digest.

```text
TIME   ACTOR                 ACTION                                  TARGET
│
├───►  User                  Selects 2+ articles                     Selection system
│
├───►  User                  Taps Digest                             SelectionActionDock
│
├───►  AppContent helper     Builds descriptors from payloads        useDigest.trigger()
│
├───►  useDigest             Same URLs already available? expand()   (early return — no HTTP)
│      │
│      └─ new/different URLs:
│
├───►  useDigest             POST /api/digest                        serve.py
│
├───►  serve.py              Delegates                               tldr_app.generate_digest()
│
├───►  tldr_app              Delegates                               tldr_service.generate_digest()
│
├───►  tldr_service          Canonicalizes URLs                      util.canonicalize_url()
│
├───►  tldr_service          Parallel content fetch                  summarizer.url_to_markdown()
│
├───►  tldr_service          Cache lookup                            storage_service.get_digest()
│      │
│      ├─ cache hit ───────► returns markdown + metadata             client
│      │
│      └─ cache miss
│            ├──► fetch digest prompt                               summarizer._fetch_digest_prompt()
│            ├──► build prompt                                      summarizer._build_digest_prompt()
│            ├──► call LLM                                          summarizer._call_llm()
│            └──► persist                                            storage_service.set_digest()
│
├───►  useDigest             Writes AVAILABLE patch + clears select  daily payload + interaction
│
└───►  useDigest             Acquires zen lock + opens overlay       DigestOverlay
```

---

## Data Flow Diagram (Matter)

> Focus: How data is transformed across the digest pipeline.

```text
[Selection IDs]      [Descriptor Build]      [Backend Synthesis]         [Persist + Render]

selectedIds ──────►  [{url,title,category}] ──► canonical URLs
                                           └──► parallel markdown fetch
                                           └──► digest prompt assembly
                                           └──► Gemini digest markdown
                                                  │
                                                  ▼
                                       {digest_id, digest_markdown,
                                        included_urls, article_count, skipped}
                                                  │
                                                  ▼
                                client digest patch stored under
                                daily payload.digest (selected target date)
                                                  │
                                                  ▼
                                  marked.parse + DOMPurify.sanitize
                                                  │
                                                  ▼
                                         DigestOverlay HTML display
```

---

## Digest State Machine

### Client persisted data state (`payload.digest.status`)

- `unknown` (implicit initial)
- `available` (digest markdown ready)
- `error` (request failed)

Transitions:

1. Trigger digest with valid selection → no persisted loading transition
2. Successful response → `available`
3. Failed response / exception (except abort) → `error`
4. Abort request → no persisted transition; last persisted state remains
5. Legacy migration: stale persisted `loading` values are normalized to `unknown` on read

### Client runtime request state (`useDigest`)

- `idle`
- `in-flight`

Transitions:

1. Trigger digest with valid selection → `in-flight`
2. Success / failure / abort / stale-token completion → `idle`

### Client view state (`expanded`)

- `collapsed`
- `expanded`

Transitions:

1. Successful digest result + zen lock acquired → `expanded`
2. Close action (button, gesture, escape) → `collapsed`

Zen lock is shared with article summary overlays so only one zen overlay can be active.

---

## Call Graph (Logic)

```text
AppContent()
├── useInteraction()
├── useDigest(results)
├── SelectionActionDock.onTriggerDigest()
│   └── useDigest.trigger(articleDescriptors)
│       ├── fetch('/api/digest')
│       ├── success path
│       │   ├── writeDigest(status=available, markdown, urls, metadata)
│       │   ├── clearSelection()
│       │   └── expand() -> acquireZenLock('digest')
│       └── error path
│           └── writeDigest(status=error, errorMessage)
└── DigestOverlay(html, expanded, ...)

Flask route stack
serve.digest_endpoint()
└── tldr_app.generate_digest(articles, effort)
    └── tldr_service.generate_digest(articles, effort)
        ├── normalize_summarize_effort()
        ├── util.canonicalize_url() per article
        ├── _fetch_articles_content_parallel()
        │   └── summarizer.url_to_markdown() per article (ThreadPoolExecutor)
        ├── storage_service.get_digest(digest_id)
        ├── summarizer._fetch_digest_prompt()
        ├── summarizer._build_digest_prompt()
        ├── summarizer._call_llm()
        └── storage_service.set_digest(...)
```

---

## API Contract

### `POST /api/digest`

Request body:

```json
{
  "articles": [
    {"url": "https://...", "title": "...", "category": "..."}
  ],
  "effort": "low"
}
```

Successful response:

```json
{
  "success": true,
  "digest_id": "<sha256>",
  "digest_markdown": "...",
  "article_count": 3,
  "included_urls": ["..."],
  "skipped": [{"url": "...", "reason": "..."}]
}
```

---

## Persistence Model

Digest data is persisted in two places with different roles:

1. **Server cache (canonical digest artifact)**
   - `digests` table keyed by `digest_id`.
   - Enables backend cache hits for identical canonical URL-set + effort.

2. **Client daily payload (UI-local recall for selected date context)**
   - `payload.digest` stored under the most recent selected date key.
   - Preserved in client merge flow (`mergePreservingLocalState`).
