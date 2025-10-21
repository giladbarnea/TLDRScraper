# Client-Side Local Storage Architecture

## Context: original user request

Discard completely from backend storage and move 100% of the storage in the app, as well as 100% of the storage responsibility, to the client-side's local storage.
Expected stateless backend requests and significant architecture simpliciation.

## Design

This document expands the "everything lives in the browser" design by mapping each feature to its client-owned data and event sequence. The browser is the sole source of truth: every user action mutates in-memory state first, immediately mirrors that change to `localStorage`, and renders directly from the hydrated objects. No other persistence layer exists.

## Local Storage Keys and Shapes

| Key | Shape | Purpose |
| --- | ----- | ------- |
| `tldr:scrapes:<ISO-date>` | `{ articles: Article[], issues: Issue[], cachedAt: ISO-string }` | Stores the newsletter payload for a specific day. Each `Article` carries summary, TLDR, removal, and read flags. |

`Article` objects include the fields below; they are the *only* authority for card rendering.

```
type Article = {
    url: string;              // canonical key
    title: string;
    issueDate: string;        // same ISO date used in key
    section: string | null;
    removed: boolean;
    summary: {
        status: 'unknown' | 'available' | 'creating' | 'error';
        markdown?: string;
        effort: 'low' | 'medium' | 'high';
        checkedAt?: ISO-string;
        errorMessage?: string;
    };
    tldr: {
        status: 'unknown' | 'available' | 'creating' | 'error';
        markdown?: string;
        effort: 'low' | 'medium' | 'high';
        checkedAt?: ISO-string;
        errorMessage?: string;
    };
    read: {
        isRead: boolean;
        markedAt?: ISO-string;
    };
};
```

`Issue` objects mirror the current cache format (metadata, sections) and are unchanged.

---

## Summaries → `"Available"` UI State

### Flow A – Hydrate daily payload

```
User opens dashboard
        ↓
HydrateController
        ├─ readLocal('tldr:scrapes:<date>')
        │       ↓
        │   hit → hydrate in-memory store exactly as saved (including summary/tldr/read state)
        │   miss → fetchNewsletter(date)
        │           ↓
        │       normalize articles → set summary.status='unknown'
        │       writeLocal('tldr:scrapes:<date>', payload)
        └─ Renderer draws cards from hydrated store
```

### Flow B – User requests summary

```
User clicks Summary button
        ↓
SummaryController
        ├─ lookup article from in-memory store (already hydrated from localStorage)
        ├─ if article.summary.markdown exists
        │       ↓
        │   toggle inline view
        │   markArticleAsRead()
        ├─ else if status !== 'creating'
        │       ↓
        │   set status='creating', writeLocal()
        │   fetch('/api/summarize-url', { method: 'POST', body: { url } })
        │       ↓
        │   on success → persist markdown, status='available'
        │   on failure → status='error', set errorMessage
        │   writeLocal()
        └─ Renderer reacts to state: shows markdown, spinner, or error message
```

*Outcome:* `Article.summary.status` flips to `'available'` only when `article.summary.markdown` is stored locally, so the UI and persistence are always in lockstep.

---

## TLDR → `"Available"` UI State

### Flow C – Hydrate TLDR state

```
HydrateController completes Flow A
        ↓
Articles in memory already include whatever TLDR state localStorage held
        ↓
Renderer labels TLDR buttons directly from article.tldr.status
```

### Flow D – User requests TLDR creation

```
User clicks TLDR button
        ↓
TldrController
        ├─ read article from store
        ├─ if tldr.markdown exists → toggle display, mark as read
        ├─ else if status !== 'creating'
        │       ↓
        │   set status='creating', writeLocal()
        │   fetch('/api/tldr-url', { method: 'POST', body: { url } })
        │       ↓
        │   on success → status='available', markdown=resp.tldr_markdown
        │   on failure → status='error', errorMessage
        │   writeLocal()
        └─ Renderer shows TLDR markdown / spinner / error based on state
```

*Outcome:* TLDR availability is always inferred from `Article.tldr.status`, which only becomes `'available'` after the TLDR markdown is persisted locally.

---

## Marked as Read State

The read toggle is purely client-owned; it never reaches the server.

### Flow E – Automatic mark-as-read when content is expanded

```
Summary or TLDR expansion completes
        ↓
ReadStateManager
        ├─ if article.read.isRead already true → no-op
        ├─ else
        │       ↓
        │   set article.read = { isRead: true, markedAt: now }
        │   writeLocal('tldr:scrapes:<date>')
        └─ Renderer adds "Read" styling instantly
```

### Flow F – Manual mark/unmark control (e.g., checkbox or bulk action)

```
User toggles "Mark as read" control
        ↓
ReadStateManager
        ├─ lookup all targeted articles
        ├─ update read.isRead flag per action
        ├─ writeLocal()
        └─ Renderer syncs badges + collapse state
```

*Interaction with other subsystems:* Because `Article.read.isRead` lives inside the same record that holds summary and TLDR metadata, any subsequent hydration (Flow A, and the TLDR reflection in Flow C) replays the read state alongside other fields. No cross-store reconciliation is required.

---

## Cross-Feature Observations

* The same `Article` payload drives every card. Inline mutations (hydration, summary requests, TLDR requests, read toggles) update the record and immediately write the full object back to the owning day key, so future sessions or tabs start from the latest state.
* Because each flow writes through the same serialization path, clearing localStorage or switching browsers simply resets the experience—there is no orphaned state elsewhere.

---

## Required Backend Changes

To make the backend align with this client-only storage model, every server component that currently reads or writes blob storage must be removed or rewritten to become stateless helpers. The list below captures all affected modules and call paths.

### Remove blob persistence stack entirely

* Delete `blob_store.py`, `blob_cache.py`, `removed_urls.py`, and `cache_mode.py`, along with their exports and environment variable requirements (`BLOB_STORE_BASE_URL`, `BLOB_READ_WRITE_TOKEN`, `FORCE_CACHE_MODE`).
* Eliminate `CACHE_SYSTEM.md` and any documentation that assumes blob-backed caches, ensuring `setup.sh` and `requirements.txt` no longer mention the removed environment knobs (grep the codebase for the env var names).

### Rework newsletter scraping to be stateless

* In `newsletter_scraper.py`, drop `_get_cached_day`, `_put_cached_day`, `_persist_day_to_cache`, cache-hit statistics, and the `removed_urls` dependency. `scrape_date_range` should always call `_collect_newsletters_for_date` and return the raw articles without annotating `removed` or reporting blob metrics.
* Remove cache-aware conditionals that guard fetches with `cache_mode.can_read()` / `can_write()`, and strip `cache_mode` imports from the file.

### Simplify summarizer pipeline

* In `summarizer.py`, remove the `@blob_cache.blob_cached` decorators, the pathname helpers (`summary_blob_pathname`, `tldr_blob_pathname`, `_url_content_pathname`), and any blob write semantics. The summarizer should always scrape content, call the LLM, and return markdown without persisting it.
* Update `tldr_service.py` to drop the `cache_only` flag, blob pathname lookups, and blob URL fields. Responses should only echo the canonical URL, effort level, and freshly generated markdown.

### Collapse application services to the new contracts

* Rewrite `tldr_app.py` so that it proxies only the remaining service calls (scrape, summarize, TLDR, prompt fetch). Remove cache-management helpers, removal endpoints, and any references to blob storage or cache modes.
* Prune CLI commands in `cli.py` accordingly: delete `--cache-only` options, drop the `remove-url`, `removed-urls`, `cache-mode`, `invalidate-cache`, and `invalidate-date-cache` subcommands, and simplify error payloads that referenced blob persistence.
* Align `scripts/cli_sanity_check.sh` with the reduced CLI surface so it only probes scrape, summary, TLDR, and prompt flows.

### Update HTTP layer and UI scaffolding

* In `serve.py`, remove the `/api/remove-url`, `/api/removed-urls`, and `/api/cache-mode` endpoints, along with cache-only request handling in the summary and TLDR routes. Ensure `api/index.py` still re-exports the trimmed Flask app.
* Clean up `templates/index.html` to eliminate cache statistics (`blob_store_present`, cache hits/misses), cache-only fetch calls, and server-driven removal toggles, relying purely on the client’s localStorage state.

### Clean supporting utilities

* Remove helper functions in `util.py` or other modules that were only used for blob bookkeeping (for example, `util.LOGS` debug dumps if they were exclusively surfaced through blob-backed stats).
* Audit tests and prompt files to make sure nothing references blob persistence or removal endpoints; adjust `package.json` scripts, API routes, and any deployment manifests to match the leaner backend.


