Subagent No. 1
==============

### Task
Identify major user-facing features and interactions provided by TLDRScraper, grouped by feature area.

### Result
Features grouped by interaction surface:
- Newsletter scraping: user submits start_date/end_date via CLI (`scrape`) or POST `/api/scrape` to trigger `tldr_app.scrape_newsletters`.
- Prompt inspection: user fetches summarize or TLDR prompt templates via CLI (`prompt`, `tldr-prompt`) or GET `/api/prompt`.
- URL summarization: user posts URL, cache_only, summary_effort through CLI (`summarize-url`) or POST `/api/summarize-url` to request summary markdown and blob references.
- URL TLDR generation: user mirrors summarization workflow through CLI (`tldr-url`) or POST `/api/tldr-url` to request TLDR markdown and blob references.
- URL removal management: user marks URLs as removed (CLI `remove-url`, POST `/api/remove-url`) and lists removals (CLI `removed-urls`, GET `/api/removed-urls`).
- Cache mode control: user gets/sets cache mode via CLI (`cache-mode get/set`) or GET/POST `/api/cache-mode`.
- Cache invalidation: user clears day range caches (CLI `invalidate-cache`, POST `/api/invalidate-cache`) or a specific day’s article+summary cache (CLI `invalidate-date-cache`, POST `/api/invalidate-date-cache`).

---

Subagent No. 2
==============

### Task
Outline state transitions for each previously identified feature, focusing on observable states and triggers.

### Result
State transitions by feature:
- Newsletter scraping: `InputValidated` (dates parsed) → per-day loop `DayCacheCheck`. On hit, articles transition to `DayCachedLoaded`; on miss, each newsletter type runs `NetworkFetch` → `ArticleNormalized` (canonical URLs, dedup) → `RemovalFlagged` (compare removed set) → `DayCachedStored` if writes allowed. Aggregation ends in `ReportAssembled` with stats.
- Prompt inspection: `ServeTemplate` reads cached in-memory state; initial call may transition `PromptCacheEmpty` → `PromptFetched` (GitHub fetch) → `PromptCached`.
- URL summarization: `InputValidated` → `URLCanonicalized` → `EffortNormalized`. If blob cache hit, `SummaryRetrieved`; else `ContentScraped` (curl/jina) → `MarkdownRendered` → `PromptPrepared` → `LLMInvoked` → `SummaryPersisted`. Failure to find cached summary while cache_only toggled yields `CacheMissAbort`.
- URL TLDR: Mirrors summarization states, substituting TLDR prompt and `TldrPersisted` final state.
- URL removal: `InputValidated` → `URLCanonicalized` → `RemovalPersisted` (append to removed list). Listing transitions `RemovalListLoaded` → `ResponseSerialized`.
- Cache mode: `ModeRead` returns current enum. Setting transitions `ModeStringNormalized` → `ModeValidated` → `ModePersisted` → `ModeReported`.
- Cache invalidation (range): `RangeValidated` → `CandidatePathnamesEnumerated` → `ExistingEntriesListed` → per-path `DeleteAttempted` resulting in `DeleteSucceeded` or `DeleteFailed` accumulators → `SummaryReported`. Single-date invalidation: `DateValidated` → `DayCacheFetched` (optional) → `RelatedUrlsEnumerated` → `UrlArtifactsDeleted` (content+summaries) → `DayCacheDeleted` → `SummaryReported`.

---

Subagent No. 3
==============

### Task
Map major components per feature in call order from client/UI through backend layers, linking to previously defined state transitions.

### Result
Component stacks by feature:
- Newsletter scraping (`ScrapeIntake` form → `/api/scrape`): `templates/index.html` ScrapeIntake JS (validates dates → RangeValidated) → `serve.scrape_newsletters_in_date_range` (input guard → InputValidated) → `tldr_app.scrape_newsletters` → `tldr_service.scrape_newsletters_in_date_range` (logs, RangeValidated) → `newsletter_scraper.scrape_date_range` (DayCacheCheck/NetworkFetch/DayCachedStored) → `blob_store` + `cache_mode` + `removed_urls` (RemovalFlagged) → result aggregated back through stack.
- Prompt inspection (debug fetch `/api/prompt` or CLI commands): front-end `fetch('/api/prompt')` or CLI `tldr_app.get_*` → `serve.get_summarize_prompt_template`/`tldr_app.get_*` → `tldr_service.fetch_*` → `summarizer._fetch_*` hitting GitHub (PromptCacheEmpty → PromptFetched → PromptCached).
- URL summarization (`SummaryDelivery`, expand buttons, CLI `summarize-url`): client card event triggers `/api/summarize-url` (cache_only true/false) → `serve.summarize_url` → `tldr_app.summarize_url` (URLCanonicalized/EffortNormalized) → `tldr_service.summarize_url_content` → `summarizer.summarize_url` decorated by `blob_cache.blob_cached` (`SummaryRetrieved` on hit, else ContentScraped → MarkdownRendered → LLMInvoked) → `blob_store` for persisted markdown.
- URL TLDR (`TldrDelivery`, CLI `tldr-url`): similar path via `/api/tldr-url` → `serve.tldr_url` → `tldr_app.tldr_url` → `tldr_service.tldr_url_content` → `summarizer.tldr_url` (`TldrPersisted`) → blob cache/store.
- URL removal (`RemovalLifecycle` UI → `/api/remove-url` or CLI `remove-url`): button click posts to server → `serve.remove_url` → `tldr_app.remove_url` → `tldr_service.remove_url` (`RemovalPersisted` in `removed_urls` module) updating file-backed set; `templates` updates card classes (RemovalFlagged state).
- Removed list (`fetch('/api/removed-urls')` or CLI `removed-urls`): UI command or CLI → `serve.get_removed_urls`/`tldr_app.list_removed_urls` → `removed_urls.get_removed_urls` (RemovalListLoaded) → response.
- Cache mode (`CacheModeControl` UI → `/api/cache-mode` or CLI `cache-mode`): GET path to `serve.get_cache_mode` → `tldr_app.get_cache_mode` → `cache_mode.get_cache_mode` (ModeRead). POST path to `serve.set_cache_mode` → `tldr_app.set_cache_mode` → `cache_mode.set_cache_mode` (ModeValidated → ModePersisted) with underlying env-backed storage.
- Cache invalidation (UI `DateCacheClear`/`RangeCacheInvalidate`): `/api/invalidate-cache` posts → `serve.invalidate_cache_in_date_range` → `tldr_app.invalidate_cache_in_date_range` (CandidatePathnamesEnumerated → DeleteAttempted) using `blob_store`. `/api/invalidate-date-cache` posts → `serve.invalidate_cache_for_date` → `tldr_app.invalidate_cache_for_date` (DayCacheFetched → UrlArtifactsDeleted → DayCacheDeleted).

---

Subagent No. 4
==============

### Task
Detail precise call graphs for each feature, recording value handoffs and resulting state across layers. Add inline comments mirroring this mapping where most relevant.

### Result
Call graphs with value flow:
- Newsletter scraping: UI `ScrapeIntake` submit serializes `{start_date, end_date}` → POST `/api/scrape`. `serve.scrape_newsletters_in_date_range` parses JSON, forwards raw strings to `tldr_app.scrape_newsletters`, which simply relays to `tldr_service.scrape_newsletters_in_date_range`. `_parse_date_range` converts to `datetime` (state `InputValidated`) and enforces limits before calling `newsletter_scraper.scrape_date_range(start_date: datetime, end_date: datetime)`. Inside `scrape_date_range`, loop constructs `date_str` per day, calls `_get_cached_day(date_str)`; on hit, articles marked `fetched_via='day_cache'` and deduped. On miss, `_fetch_newsletter(date, newsletter_type)` returns article dicts with `fetched_via` indicating network; canonicalization ensures stable URLs, `removed_urls` set is consulted to toggle `article['removed']`. If `cache_mode.can_write()`, `_put_cached_day` persists sanitized day payload via `blob_store.put_file`. Final `output` includes grouped markdown via `_format_final_output`, aggregated stats bubble back to HTTP response.
- Prompt inspection: CLI `prompt`/`tldr-prompt` or GET `/api/prompt` call `tldr_app.get_*` → `tldr_service.fetch_*` → `summarizer._fetch_*`. On first call `_PROMPT_CACHE`/`_TLDR_PROMPT_CACHE` is empty (state `PromptCacheEmpty`); GitHub API request uses optional `GITHUB_API_TOKEN`. Successful text cached in module globals, so subsequent calls short-circuit.
- URL summarization: UI `SummaryDelivery` preflight or on-demand expanders compose JSON `{url, cache_only, summary_effort}` and POST `/api/summarize-url`. `serve.summarize_url` forwards to `tldr_app.summarize_url`, which canonicalizes URL and propagates `cache_only` & normalized effort (state `URLCanonicalized`). `tldr_service.summarize_url_content` calls `summarizer.summarize_url` wrapped by `blob_cache.blob_cached(summary_blob_pathname)`. Decorator builds pathname (e.g., `<url>-summary[-effort].md`), checks blob read availability: if `cache_only` and `cache_mode.can_read()` is false, returns `None`; if blob hit, returns cached markdown (`SummaryRetrieved`). On miss, wrapper calls `summarizer.summarize_url(canonical_url, summary_effort)` which sequences `url_to_markdown` (internally `scrape_url` choosing curl_cffi → jina fallback), `_fetch_summarize_prompt`, `_insert_markdown_into_template`, `_call_llm` with OpenAI `reasoning.effort`. Result streamed back; wrapper optionally `put_file` via blob store if `cache_mode.can_write()`. `tldr_service` adds blob URLs/pathnames and canonical URL before HTTP response.
- URL TLDR: Same HTTP/CLI flow using `/api/tldr-url` and `tldr_app.tldr_url`. Decorator `blob_cache.blob_cached(tldr_blob_pathname)` caches TLDR markdown under `<url>-tldr[-effort].md`. Prompt pipeline uses `_fetch_tldr_prompt` and `_call_llm`. Response includes TLDR-specific fields.
- URL removal: UI `RemovalLifecycle` posts `{url}` to `/api/remove-url` or CLI `remove-url`. `serve.remove_url` → `tldr_app.remove_url` canonicalizes and calls `tldr_service.remove_url`, which validates scheme, writes canonical URL to storage via `removed_urls.add_removed_url`, returning canonical URL. Frontend marks card `.removed`; CLI prints JSON with `canonical_url`.
- Removed list: `/api/removed-urls` or CLI hits `tldr_app.list_removed_urls`, which wraps `removed_urls.get_removed_urls()` (iterable backed by JSON file) and serializes as list.
- Cache mode: UI GET `/api/cache-mode` or CLI `cache-mode get` → `tldr_app.get_cache_mode` returning enum `.value`. Setting uses `/api/cache-mode` POST or CLI `cache-mode set --mode`, hitting `tldr_app.set_cache_mode` which normalizes, validates against `cache_mode.CacheMode`, invokes `cache_mode.set_cache_mode` (writes to file under `cache_mode._CACHE_MODE_FILE`), then echoes value.
- Cache invalidation range: UI/CLI posts `{start_date, end_date}`. `tldr_app.invalidate_cache_in_date_range` parses via `datetime.fromisoformat`, builds potential day pathnames using `blob_store.build_scraped_day_cache_key`, filters existing entries via `blob_store.list_existing_entries`, loops deleting with `blob_store.delete_file`, tracking successes/failures; response includes counts and `errors` list.
- Cache invalidation single date: payload `{date}`. `tldr_app.invalidate_cache_for_date` fetches day cache JSON via HTTP GET to blob base, extracts article URLs to build canonical URL base pathnames, deletes article markdown plus summary permutations for each `SUMMARY_EFFORT_OPTIONS`, then deletes the day cache entry itself. Response lists `deleted_files` sample and failure info.

Inline code comments were added in `tldr_app.summarize_url` and `tldr_app.invalidate_cache_in_date_range` to reflect these pipelines for future subagents.

---
