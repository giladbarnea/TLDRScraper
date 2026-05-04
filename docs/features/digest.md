---
name: features/digest
description: End-to-end architecture of the Digest feature including elaboration and caching.
last_updated: 2026-05-04 16:28
---
# Digest Feature Architecture

## Overview

The Digest feature lets a user select multiple feed articles and generate a single synthesized AI digest. Once open, the digest overlay supports **Elaboration**: selecting text inside the rendered digest and asking the LLM to expand on it, using all source articles as context. The elaboration feature is shared with single-article summaries (`ZenModeOverlay`) via the `useElaboration` hook and the overlay context menu contract.

The digest domain spans client selection state, client overlay/state persistence, backend orchestration, content extraction, Gemini generation, server-side digest caching, and elaboration.

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
│  │   articleStore selected slices / descriptors                      │  │
│  │            │                                                      │  │
│  │            ▼                                                      │  │
│  │   SelectionActionDock.digest ─────► useDigest hook               │  │
│  │                                (request + persistence + zen lock) │  │
│  │                                            │                      │  │
│  │                                            ▼                      │  │
│  │                                       DigestOverlay               │  │
│  │                             (portal + gestures + rendered HTML)   │  │
│  │                                       │                           │  │
│  │  ┌────────────────────────────────────┼────────────────────────┐  │  │
│  │  │  Overlay Context Menu + Elaboration (shared with Zen)        │  │  │
│  │  │   useOverlayContextMenu → BaseOverlay (overlayMenu contract) │  │  │
│  │  │   useElaboration → ElaborationPreview (overlayLayers slot)   │  │  │
│  │  │   POST /api/elaborate                                        │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
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
├───►  AppContent helper     Reads selected descriptors              useDigest.trigger()
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
├───►  useDigest             Writes AVAILABLE patch + clears select  articleStore + mutation queue
│
└───►  useDigest             Acquires zen lock + opens overlay       DigestOverlay
```

---

## Data Flow Diagram (Matter)

> Focus: How data is transformed across the digest pipeline.

```text
[Selection IDs]      [Descriptor Build]      [Backend Synthesis]         [Persist + Render]

selected descriptors ─►  [{url,title,category}] ─► canonical URLs
                                           └──► parallel markdown fetch
                                           └──► digest prompt assembly
                                           └──► Gemini digest markdown
                                                  │
                                                  ▼
                                       {digest_id, digest_markdown,
                                        included_urls, article_count, skipped}
                                                  │
                                                  ▼
                                client digest patch applied to
                                articleStore day slice + daily payload
                                                  │
                                                  ▼
                                  marked.parse + DOMPurify.sanitize
                                                  │
                                                  ▼
                                         DigestOverlay HTML display
```

---

## Digest State Machine

> **Note:** For exhaustive details on digest state transitions, runtime request states, view states, and how it shares the Zen lock with single-article summaries, see [State Machines: Articles and Summaries](../state-machines/articles-and-summaries.md) and [Client: Summaries and Digests](../client/summaries-and-digests.md).

### Client persisted data state (`payload.digest.status`)
- `unknown` → `available` → `error`

### Client view state (`expanded`)
- `collapsed` ↔ `expanded` (acquired via Zen lock)

---

## Call Graph (Logic)

```text
AppContent()
├── useSelectedDescriptors()
├── useDigest(results)
├── SelectionActionDock.onTriggerDigest()
│   └── useDigest.trigger(articleDescriptors)
│       ├── fetch('/api/digest')
│       ├── success path
│       │   ├── queueDailyPayloadPatch(status=available, markdown, urls, metadata)
│       │   ├── interactionActions.clearSelection()
│       │   └── expand() -> acquireZenLock('digest')
│       └── error path
│           └── queueDailyPayloadPatch(status=error, errorMessage)
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

## Elaboration in Digest

While reading a digest, the user can select text → right-click (desktop) or lift finger after native selection (mobile) → choose "Elaborate". The backend scrapes all source articles in parallel (max 5 workers) and feeds their concatenated bodies to the LLM alongside the selected text and the digest markdown.

### Client-side wiring & Layer stack

> **Note:** The DOM layer contracts, `FloatingTree` usage, mobile selection reducers, and hook wiring (`useOverlayContextMenu` + `useElaboration`) are identical to `ZenModeOverlay`. For all UI and state details, see [Client: Context Menu](../client/context-menu.md) and [State Machines: Context Menu](../state-machines/context-menu.md).

### Backend

`POST /api/elaborate` → `tldr_app.elaborate()` → `tldr_service.elaborate_content()` → parallel `_fetch_article_markdowns_parallel()` (max 5 workers) → `summarizer.elaborate()` → `_build_elaborate_prompt()`. Canonicalizes each URL, scrapes all in parallel, concatenates bodies into `<source-articles>` (per-article `<article index="N">...</article>` delimiters when N > 1), and returns `{ elaboration_markdown, canonical_urls }`.

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

### `POST /api/elaborate`

Request body:

```json
{
  "selected_text": "...",
  "source_markdown": "...",
  "article_urls": ["https://...", "https://..."]
}
```

Successful response:

```json
{
  "success": true,
  "elaboration_markdown": "...",
  "canonical_urls": ["https://...", "https://..."]
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
   - Reflected in the `articleStore` day slice and persisted with `queueDailyPayloadPatch()`.
   - Preserved in client merge flow (`mergeDayFromServer()`).
