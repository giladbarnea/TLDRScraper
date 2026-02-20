---
last_updated: 2026-02-20 07:52
---
# Article Digest Feature — Architecture Plan

## Pass 1: High-Level Architecture

### What the feature does

The user selects multiple articles from the feed (via the existing long-press selection system), taps a "Digest" action, and receives a single AI-generated synthesis of all selected articles' contents. The digest is displayed in a ZenOverlay and persisted so it can be recalled without regeneration.

### Inputs and Outputs

**Input (user-facing):** A set of selected articles — anywhere from 2 to ~20, possibly spanning multiple dates and sources.

**Input (to backend):** A list of article URLs with metadata (title, category, source). Optionally, a summarization effort level.

**Output (from backend):** A single markdown document that synthesizes the selected articles — drawing out themes, connections, key takeaways, and per-article highlights with source attribution.

**Output (user-facing):** The digest rendered as sanitized HTML in a full-screen ZenOverlay, with the same gesture vocabulary as the existing summary overlay (pull-to-close, scroll progress, overscroll-to-mark-complete).

### End-to-End Data Flow

```
User long-presses to select articles in Feed
    ↓
SelectionCounterPill shows count; new DigestButton appears
    ↓
User taps DigestButton
    ↓
Client extracts article URLs + metadata from selectedIds × payloads
    ↓
POST /api/digest  { articles: [{url, title, category}, ...], effort }
    ↓
serve.py → tldr_app.generate_digest() → tldr_service.generate_digest()
    ↓
For each article URL (parallel):  summarizer.url_to_markdown(url)
    ↓
Build multi-article prompt:  digest template + tagged article blocks
    ↓
summarizer._call_llm(prompt, effort)
    ↓
Return { success, digest_markdown, article_urls, article_count }
    ↓
Client receives response → renders markdown → HTML via marked.js + DOMPurify
    ↓
DigestOverlay opens (portal, zen lock acquired)
    ↓
Digest persisted to storage alongside article data
```

### Where the digest lives in the existing architecture

The digest sits at the intersection of three existing systems:

1. **Selection system** (InteractionContext) — provides the "which articles" input. The digest is the first batch action to consume `selectedIds`.
2. **Summary/TLDR system** (useSummary, summarizer.py) — the digest is architecturally analogous. It reuses the same content-extraction pipeline, LLM call infrastructure, and markdown → HTML rendering pipeline.
3. **Storage system** (useSupabaseStorage, daily_cache) — the digest result needs persistence, and the existing pub/sub cache provides the reactive layer.

The digest does *not* touch the scraping/adapter system, the newsletter config system, or the article lifecycle reducer (Domain A) — it is read-only with respect to article data.

---

## Pass 2: Module-Level Enrichment

### Client: Selection → Digest Trigger

**Current state:** The selection system exposes `selectedIds` (Set) and `isSelectMode` (boolean) via `useInteraction()`. `SelectionCounterPill` renders in the header when selection is active. No batch actions consume the selection today.

**What changes:**
- A new **DigestButton** component, visible only when `isSelectMode` is true, placed adjacent to SelectionCounterPill in the App.jsx header area.
- DigestButton receives `payloads` (from `results.payloads`) as a prop. When tapped, it flattens payloads to an article array, filters by `selectedIds` (matching `article-${url}`), extracts `{url, title, category, sourceId}` per article, and initiates the digest flow.
- The extraction logic could be a pure utility function taking `(selectedIds, payloads) → articleDescriptors[]`.
- After digest generation completes, `clearSelection()` should be called. On error, selection should be preserved to allow retry.
- **UX guardrail worth considering:** A selection size cap or confirmation dialog when the selection is large (e.g., >15 articles), since digest quality and latency degrade with very large inputs.

**Divergence from existing patterns:** The selection system today is purely visual — it selects but never acts. DigestButton introduces the first consumer of selection state, coupling the interaction layer to a data-fetching side effect. This is a one-way dependency (digest reads from selection, not the other way), so the coupling is acceptable.

### Client: Digest State Management

**Pattern to follow:** The `useSummary` hook is the closest analog. It manages fetch lifecycle (idle → loading → available / error), zen lock acquisition, abort/rollback, and persistence through `useArticleState`.

**What changes:**
- A new **useDigest** hook, similar in shape to `useSummary` but operating on a set of articles rather than one.
- State machine: `idle → loading → available / error`. Could reuse `summaryDataReducer.js` if the state shape is identical (status, markdown, effort, checkedAt, errorMessage), or a lightweight variant if digest-specific fields are needed (e.g., `articleUrls`).
- The hook manages fetch lifecycle: POST to `/api/digest`, handle response, acquire zen lock, set expanded.
- Unlike `useSummary` which is per-article (many instances), `useDigest` would be a singleton — one digest at a time at the App level.
- The hook could live in App.jsx or in a context, since it's not per-card. The digest result is transient to the current session but persisted to storage.

**Divergence:** `useSummary` is instantiated per-ArticleCard and stores data inside each article object in the payload. The digest is not per-article — it's a cross-article derived artifact. This means the storage location and data shape differ (see Storage section below).

### Client: Digest Overlay

**Pattern to follow:** ZenModeOverlay (defined inside ArticleCard.jsx).

**What changes:**
- A new **DigestOverlay** component, structurally identical to ZenModeOverlay: portal to `document.body`, fixed position, `z-[100]`, gestures (pull-to-close, scroll progress), keyboard (Escape to close).
- **Header differences:** Instead of a single domain/favicon link, the header would show the article count ("5 articles") and possibly a condensed list of sources/categories.
- `onClose` collapses the overlay and releases zen lock.
- `onMarkComplete` (the overscroll gesture) could mark all digested articles as read, or do nothing for the MVP.
- The markdown → HTML pipeline is identical: `marked.parse()` → `DOMPurify.sanitize()`.

**Reuse vs. build fresh:**
- The gesture hooks (`useOverscrollUp`, `usePullToClose`, `useScrollProgress`) are fully reusable — they take refs and callbacks, no coupling to ArticleCard.
- The overlay shell (portal, fixed layout, header, scroll container) could potentially be extracted into a shared `OverlayShell` component that both ZenModeOverlay and DigestOverlay use. However, if that extraction feels premature, building DigestOverlay as a standalone component following the same pattern is also fine — two similar components is not a problem when their headers and behaviors diverge.

**Zen lock:** The digest overlay should share the same zen lock as single-article overlays. Only one overlay (digest or article) can be open at a time. The lock owner for a digest could be `digest-${hash}` or simply `'digest'`. If a single-article overlay is open when the user taps Digest, the digest action should either close the existing overlay first or be blocked.

### Backend: API Endpoint

**Pattern to follow:** The `/api/summarize-url` endpoint chain: `serve.py` → `tldr_app.py` → `tldr_service.py`.

**What changes:**
- New route: `POST /api/digest` in `serve.py`.
- Request body: `{ articles: [{url, title, category}, ...], effort: "low" }`.
- Response: `{ success: true, digest_id: "...", digest_markdown: "...", article_count: N, included_urls: [...], skipped: [{url, reason}] }`.
- The `digest_id` is a stable hash of sorted canonical URLs + effort level, enabling cache hits on repeated selections. Treating digests as **immutable-by-default** (regenerate = new ID when inputs change) simplifies race concerns.
- `included_urls` and `skipped` explicitly communicate which articles made it into the digest, which is important when partial scraping failures occur.
- Error handling follows existing convention: ValueError → 400, RequestException → 502, generic → 500.
- App layer (`tldr_app.py`): thin pass-through `generate_digest()` that delegates to service layer and shapes the response.
- Service layer (`tldr_service.py`): `generate_digest()` that validates input, orchestrates content fetching, builds the prompt, and calls the LLM.

**Content fetching:** The service layer should call `summarizer.url_to_markdown(url)` for each article, in parallel via `ThreadPoolExecutor` (existing pattern from scrape orchestration). Partial failures should be handled gracefully — if 3 out of 5 articles fail to scrape, the digest should be generated from the 2 that succeeded, with a note about the failures.

### Backend: Prompt Engineering

**Pattern to follow:** `summarizer._fetch_summary_prompt()` fetches a template from GitHub.

**What changes:**
- A new digest prompt template, either:
  - Stored alongside the TLDR template in the `llm-templates` GitHub repo (e.g., `text/digest.md`).
  - Or hardcoded initially and extracted later.
- The prompt structure wraps each article's markdown in metadata tags:
  ```
  {digest_template}

  <articles>
  <article title="..." source="..." url="...">
  {markdown_content}
  </article>
  ...
  </articles>
  ```
- The template should instruct Gemini to synthesize themes, find connections, highlight key takeaways, and attribute insights to their source articles.

**Token management — the critical concern:**
- Combined content from 5-10 articles could easily exceed 100K tokens. Gemini 3 Pro has a large context window, but quality degrades with very long prompts.
- **Recommended strategy for MVP:** Truncate each article's markdown to a reasonable length (e.g., first ~3000 words) before including in the prompt. If total estimated token count exceeds a threshold, progressively truncate further.
- **Future consideration:** A two-pass approach (summarize each article individually, then meta-summarize the summaries) would be more robust but doubles latency and API cost.

### Backend: Storage and Persistence

**The key question:** Where does the digest live in Supabase?

The digest is a cross-article artifact. It doesn't naturally belong to a single article (unlike per-article summaries) or a single date (selected articles may span dates).

**Option A — Embed in `daily_cache` payloads:**
- Add a `digests` array to the daily payload: `{ date, articles, issues, digests: [...] }`.
- Each digest entry: `{ id: urlHash, markdown, articleUrls, generatedAt, status }`.
- For multi-date selections, store the digest in the most recent date's payload.
- Pros: zero infrastructure changes. Cons: awkward fit for multi-date digests; digest lifecycle coupled to daily payload writes; `mergePreservingLocalState` needs to handle `digests` field.

**Option B — Settings table with computed key:**
- Store as `digest:{urlSetHash}` in the settings table.
- Pros: independent lifecycle, works for any article combination. Cons: semantically wrong (settings ≠ content); no date queries; stale digests accumulate.

**Option C — New `digests` table:**
- `CREATE TABLE digests (id TEXT PRIMARY KEY, digest JSONB NOT NULL, generated_at TIMESTAMPTZ DEFAULT NOW())`.
- ID = stable hash of sorted canonical article URLs + effort level. Including effort in the hash means re-generating at a different effort level creates a new entry rather than overwriting.
- Digests are treated as immutable: once generated, the row is never updated. Regeneration creates a new row with a new ID. This eliminates update races and simplifies caching.
- Pros: semantically correct, independent lifecycle, can add indexes, natural fit for cross-date selections. Cons: requires Supabase migration, new CRUD in `storage_service.py`, new routes.

**Recommendation:** Start with **Option A** for MVP. The digest is conceptually "derived from today's articles" in most use cases. If multi-date digests or digest history become important, migrate to Option C. The key consideration is that `mergePreservingLocalState` must treat `digests` as a client-state field (not overwritten by fresh scrape data), similar to how `summary` and `read` are preserved on articles.

### Client: Storage Integration

**If Option A (daily_cache embed):**
- The digest data flows through the existing `useSupabaseStorage` pub/sub system. No new storage keys needed.
- `useDigest` writes the digest into the daily payload alongside articles, using the same `setValueAsync` → `emitChange` pattern.
- The digest could be read back from the payload on subsequent loads.
- Storage key routing remains unchanged: `newsletters:scrapes:{date}` → daily_cache.

**If Option C (new table):**
- New key pattern: `digest:{hash}` → `digests` table.
- New routing case in `useSupabaseStorage.readValue()` and `writeValue()`.
- New backend routes: `GET/POST /api/storage/digest/{id}`.
- New functions in `storage_service.py`: `get_digest(id)`, `set_digest(id, data)`.

---

## Risks and Upstream/Downstream Concerns

### Likely to need attention:

1. **`mergePreservingLocalState` (App.jsx):** If digests are stored in daily_cache payloads, the `SERVER_ORIGIN_FIELDS` list and merge logic need to be aware of the `digests` field. If `digests` is not in `SERVER_ORIGIN_FIELDS`, it will be preserved automatically (good). But if a background rescrape builds a fresh payload without `digests`, and the merge only maps over `freshPayload.articles`, the `digests` field from the local payload could be silently dropped. The merge function would need to explicitly carry over `digests` from the local payload.

2. **Zen lock contention:** If a single-article overlay is open, tapping Digest would fail to acquire the lock. The UX needs to handle this — either auto-close the existing overlay or disable the Digest button while an overlay is active.

3. **Selection reset on page reload:** `selectedIds` is ephemeral (not persisted). If the user selects articles, triggers digest generation, and the page reloads mid-flight, the selection is lost. The digest request is already in-flight and will complete server-side, but the client won't know what to do with the response. Mitigation: the digest endpoint is stateless — if the client reconnects, it can re-request from the persisted digest.

4. **Content scraping latency:** Fetching markdown for N articles is N network requests. Even in parallel, 10 articles could take 10-30 seconds. The client needs a loading state that communicates progress. The existing `LOADING` status works, but a progress indicator (e.g., "Fetching article 3 of 10...") would improve UX. The backend could potentially return a streaming response, but this is a future enhancement.

5. **Token overflow to Gemini:** The biggest functional risk. If combined content exceeds the model's effective capacity, the digest quality degrades or the API errors. A truncation strategy is essential for launch.

6. **Per-article summary duplication:** Some selected articles may already have cached summaries. The digest feature should use the raw article content (not the cached summary) since the digest prompt is different. However, if content scraping fails for an article but a cached summary exists, the summary could be used as a fallback — worth considering but not essential for MVP.

### Unlikely to break but worth a quick check:

7. **CalendarDay cache seeding:** If the digest modifies the daily payload shape, CalendarDay's cache seeding must still work correctly. Since seeding is based on the full payload object, adding a `digests` field should be transparent.

8. **ArticleCard rendering:** ArticleCard reads article-level fields. A payload-level `digests` field should be invisible to it. No regression expected.

9. **Background rescrape union logic:** The server-side union for "today" (cached + fresh) operates on articles. It should not touch a payload-level `digests` field. Verify that `_merge_payloads` in `tldr_service.py` doesn't strip unknown fields.

10. **URL canonicalization mismatches:** Digest identity and caching depend on canonical URLs. The client works with raw URLs from article objects, while the backend canonicalizes via `util.canonicalize_url()`. If the client sends non-canonical URLs and the backend hashes canonical URLs, repeated selections might miss the cache. The client should either send canonical URLs or let the backend canonicalize before hashing.

11. **Write amplification (Option A only):** If the digest is embedded in the daily_cache payload, every article state change (mark read, remove, etc.) rewrites the entire payload including the digest text. This increases the payload size for every write and raises the probability of read-modify-write races. This is the strongest argument for eventually moving to Option C.
