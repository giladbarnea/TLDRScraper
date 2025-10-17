# TLDRScraper Architecture

## Feature Overview and Entry Points
| User Interaction | Primary Endpoint / CLI | Core Call Stack | Dominant State Transitions |
| --- | --- | --- | --- |
| Scrape newsletters for a date range | `/api/scrape` (POST), `cli.py scrape` | `serve.scrape_newsletters_in_date_range` → `tldr_app.scrape_newsletters` → `tldr_service.scrape_newsletters_in_date_range` → `newsletter_scraper.scrape_date_range` → `blob_store`/`cache_mode`/`removed_urls` | `InputValidated` → (`DayCacheCheck` → `DayCachedLoaded` \| `NetworkFetch`) → `ArticleNormalized` → `RemovalFlagged` → `DayCachedStored` → `ReportAssembled` |
| Inspect summarize/tldr prompt templates | `/api/prompt` (GET), CLI `prompt`/`tldr-prompt` | `serve.get_summarize_prompt_template` or `tldr_app.get_*` → `tldr_service.fetch_*` → `summarizer._fetch_*` | `PromptCacheEmpty` → `PromptFetched` → `PromptCached` |
| Summarize article URL | `/api/summarize-url` (POST), CLI `summarize-url` | `serve.summarize_url` → `tldr_app.summarize_url` → `tldr_service.summarize_url_content` → `summarizer.summarize_url` (`blob_cache.blob_cached`) → `blob_store` | `InputValidated` → `URLCanonicalized` → `EffortNormalized` → (`SummaryRetrieved` \| `ContentScraped` → `MarkdownRendered` → `PromptPrepared` → `LLMInvoked` → `SummaryPersisted`) |
| Generate TLDR for URL | `/api/tldr-url` (POST), CLI `tldr-url` | `serve.tldr_url` → `tldr_app.tldr_url` → `tldr_service.tldr_url_content` → `summarizer.tldr_url` (`blob_cache.blob_cached`) → `blob_store` | Same as summarize flow, final state `TldrPersisted` |
| Mark URL as removed | `/api/remove-url` (POST), CLI `remove-url` | `serve.remove_url` → `tldr_app.remove_url` → `tldr_service.remove_url` → `removed_urls.add_removed_url` | `InputValidated` → `URLCanonicalized` → `RemovalPersisted` |
| View removed URLs | `/api/removed-urls` (GET), CLI `removed-urls` | `serve.get_removed_urls` → `tldr_app.list_removed_urls` → `removed_urls.get_removed_urls` | `RemovalListLoaded` → `ResponseSerialized` |
| Read/set cache mode | `/api/cache-mode` (GET/POST), CLI `cache-mode` | `serve.get_cache_mode`/`serve.set_cache_mode` → `tldr_app.get_cache_mode`/`tldr_app.set_cache_mode` → `cache_mode.get_cache_mode`/`cache_mode.set_cache_mode` | `ModeRead` or `ModeStringNormalized` → `ModeValidated` → `ModePersisted` → `ModeReported` |
| Invalidate caches (range) | `/api/invalidate-cache` (POST), CLI `invalidate-cache` | `serve.invalidate_cache_in_date_range` → `tldr_app.invalidate_cache_in_date_range` → `blob_store.list_existing_entries` & `blob_store.delete_file` | `RangeValidated` → `CandidatePathnamesEnumerated` → `ExistingEntriesListed` → (`DeleteSucceeded`\|`DeleteFailed`) → `SummaryReported` |
| Invalidate caches (single date) | `/api/invalidate-date-cache` (POST), CLI `invalidate-date-cache` | `serve.invalidate_cache_for_date` → `tldr_app.invalidate_cache_for_date` → `blob_store.delete_file` across article and summary assets | `DateValidated` → `DayCacheFetched` → `RelatedUrlsEnumerated` → `UrlArtifactsDeleted` → `DayCacheDeleted` → `SummaryReported` |

## URL State Machine
1. **InputValidated** – Raw URL collected (UI card, CLI, or API) and schema checked by `serve`/`tldr_app` entrypoints.
2. **URLCanonicalized** – `tldr_service` normalizes via `util.canonicalize_url`, ensuring deterministic cache keys.
3. **EffortNormalized** – Requested summary effort coerced into allowed `SUMMARY_EFFORT_OPTIONS`.
4. **SummaryRetrieved** – When `blob_cache.blob_cached` finds an existing markdown blob and returns it immediately (cache hit). If `cache_only` is `True` and no hit, transition to **CacheMissAbort** and return failure payload.
5. **ContentScraped** – Cache miss drives `summarizer.url_to_markdown`, which in turn executes `_scrape_with_curl_cffi` and, if needed, `_scrape_with_jina_reader` to acquire HTML; result rendered into Markdown (`MarkdownRendered`).
6. **PromptPrepared** – Summaries call `_fetch_summarize_prompt` and embed markdown via `_insert_markdown_into_template`; TLDR calls `_fetch_tldr_prompt` and wraps markdown with `<tldr this>` tags.
7. **LLMInvoked** – `_call_llm` sends prompt + effort to OpenAI `/v1/responses` and parses the returned text.
8. **SummaryPersisted / TldrPersisted** – On success and when `cache_mode.can_write()` is true, markdown saved to blob storage under deterministic pathname; response augmented with blob URL/path references before returning upstream.

## Article State Machine
1. **Discovered** – `newsletter_scraper.scrape_date_range` loads newsletters by date/type, either from `_get_cached_day` (cache hit) or `_fetch_newsletter` (network).
2. **ArticleNormalized** – Each article’s URL is canonicalized, deduplicated against `url_set`, and annotated with metadata such as `section_order` and `fetched_via`.
3. **RemovalFlagged** – Canonical URL compared against `removed_urls` set; articles flagged with `removed=True` for downstream UI and TLDR handling.
4. **DayCachedStored** – When write mode is enabled, sanitized article and issue lists persisted via `_put_cached_day`, enabling future `DayCachedLoaded` retrievals.
5. **SummaryLifecycle** – User-triggered summary/TLDR requests move article URL through the URL state machine above. Cached markdown attaches to cards and enables copy-to-clipboard and TLDR expansion flows in the UI.
6. **Removed** – When `/api/remove-url` succeeds, UI reclassifies card state to `.removed`; subsequent newsletter scrapes respect removal flag, and single-date invalidation prunes associated blobs.
7. **Purged** – `/api/invalidate-date-cache` or `/api/invalidate-cache` delete day cache JSON and associated markdown summaries, resetting the article to a pre-discovery state for that date.

## Call Graph Summaries
- **Scrape Flow**: UI/CLI → Flask route `serve.scrape_newsletters_in_date_range` → `tldr_app.scrape_newsletters` → `tldr_service.scrape_newsletters_in_date_range` → `newsletter_scraper.scrape_date_range` → `_get_cached_day`/`_fetch_newsletter` → `_put_cached_day` → response with stats and grouped markdown.
- **Summarize Flow**: UI SummaryDelivery or CLI → `/api/summarize-url` → `tldr_app.summarize_url` → `tldr_service.summarize_url_content` → `blob_cache.blob_cached(summary_blob_pathname)` wrapper around `summarizer.summarize_url` → `url_to_markdown` → `_call_llm` → blob persistence → JSON payload (markdown, blob URL/path, canonical URL, effort).
- **TLDR Flow**: Mirrors summarize flow using `tldr_app.tldr_url` and `summarizer.tldr_url`, storing under `-tldr` pathnames.
- **Removal Flow**: UI RemovalLifecycle or CLI → `/api/remove-url` → `tldr_app.remove_url` → `tldr_service.remove_url` → `removed_urls.add_removed_url` (file-backed) → response with canonical URL; list view hits `removed_urls.get_removed_urls`.
- **Cache Mode & Invalidation**: UI controls → `/api/cache-mode` or `/api/invalidate-*` → `tldr_app` functions invoking `cache_mode` and `blob_store` helpers to mutate or report environment-driven cache behavior.

These layers ensure every user interaction maps cleanly to a deterministic state progression for both URLs and newsletter articles, while the blob cache orchestrates persistence boundaries shared across flows.
