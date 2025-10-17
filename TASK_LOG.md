Subagent No. 1
==============

### Task
Survey the application to list major user-facing features and the interactions offered for each.

### Result
Identified primary features and grouped user interactions:
- **Newsletter scraping:** scrape TLDR newsletters over a start/end date range via CLI (`scrape`) and HTTP POST `/api/scrape`.
- **URL summarization:** generate markdown summaries for a URL with optional cache-only and effort controls via CLI (`summarize-url`) and POST `/api/summarize-url`.
- **URL TLDR generation:** create TLDR-focused markdown with the same options via CLI (`tldr-url`) and POST `/api/tldr-url`.
- **Prompt inspection:** fetch summarize or TLDR prompt templates via CLI (`prompt`, `tldr-prompt`) and GET `/api/prompt`.
- **URL removal tracking:** mark URLs as removed or list them through CLI (`remove-url`, `removed-urls`) and POST `/api/remove-url`, GET `/api/removed-urls`.
- **Cache mode control:** view or update cache behavior via CLI (`cache-mode get|set`) and GET/POST `/api/cache-mode`.
- **Cache invalidation:** clear cached scrape data (range or specific date) through CLI (`invalidate-cache`, `invalidate-date-cache`) and POST endpoints `/api/invalidate-cache`, `/api/invalidate-date-cache`.

---
Subagent No. 2
==============

### Task
For each identified feature, outline the key state transitions the code enforces for URLs, articles, and caches.

### Result
Mapped feature state transitions:
- **Newsletter scraping:** `input_pending → date_range_validated → per_day_loop`. Each day branch follows `cache_checked → (cache_hit → articles_deduped → aggregated)` or `cache_miss → newsletters_fetched → articles_normalized → day_cached`. After the loop, state advances to `removed_flag_applied → output_formatted` before returning.
- **URL summarization:** `request_received → url_canonicalized → effort_normalized → summary_lookup`. Cache decorator drives `summary_lookup → (cache_hit → respond_with_blob_refs)` or `cache_miss → page_markdown_scraped → prompt_filled → llm_called → cache_written → respond_with_blob_refs`. Canonical URL and effort label persist across states.
- **URL TLDR generation:** mirrors summarization with TLDR-specific prompt, states `request_received → url_canonicalized → effort_normalized → tldr_lookup` and the same cache hit/miss branches, ending at `respond_with_blob_refs`.
- **Prompt inspection:** single transition `request_received → prompt_cache_checked → (memory_hit → return_prompt) | (github_fetch → memory_seeded → return_prompt)`.
- **URL removal tracking:** `request_received → url_validated → canonicalized → removal_set_updated → success_response`. Listing removed URLs is `request_received → removal_set_loaded → respond_list`.
- **Cache mode control:** getter uses `request_received → cache_mode_read → respond_mode`; setter enforces `request_received → mode_string_normalized → enum_validated → cache_mode_updated → respond_mode` with failure states on invalid enum or persist failure.
- **Cache invalidation (range):** `request_received → date_inputs_validated → date_range_enumerated → pathnames_built → existing_entries_listed → deletion_loop` with each deletion `blob_delete_attempt → (delete_success | delete_failure_logged)`, finishing at `summary_compiled`.
- **Cache invalidation (single date):** `request_received → date_validated → day_blob_downloaded (best-effort) → urls_extracted → per_url_cache_cleanup` (content + per-effort summary files) → `day_cache_deleted → summary_compiled`.

---
Subagent No. 3
==============

### Task
Trace each feature from entrypoint to backend components, linking the sequence to the previously mapped state transitions.

### Result
Component stacks per feature:
- **Newsletter scraping:** UI/CLI (serve `/api/scrape` or CLI `scrape`) → `tldr_app.scrape_newsletters` → `tldr_service.scrape_newsletters_in_date_range` (validates range) → `newsletter_scraper.scrape_date_range` (day cache orchestration) → `_get_cached_day`/`_put_cached_day` + `_fetch_newsletter` (per type fetch) → `blob_store` + `removed_urls` utilities for final formatting. These align with `date_range_validated` through `output_formatted` states.
- **URL summarization:** UI/CLI (`/api/summarize-url` or CLI) → `tldr_app.summarize_url` → `tldr_service.summarize_url_content` (canonicalize + effort normalize) → `summarizer.summarize_url` decorated by `blob_cache.blob_cached` → `url_to_markdown` (GitHub special-case and HTTP fetch) → `_call_llm` OpenAI call → blob store writers. Steps map to `url_canonicalized`, cache branch, markdown scrape, prompt fill, and LLM states.
- **URL TLDR generation:** Similar path via `tldr_app.tldr_url` → `tldr_service.tldr_url_content` → `summarizer.tldr_url` (blob cache) → `url_to_markdown` → `_call_llm` with TLDR template → blob store. Mirrors `tldr_lookup` states.
- **Prompt inspection:** UI/CLI → `tldr_app.get_*_prompt_template` → `tldr_service.fetch_*_prompt_template` → `summarizer._fetch_*_prompt` (in-memory cache, GitHub fetch) hitting GitHub API when needed, covering the `prompt_cache_checked` states.
- **URL removal tracking:** UI/CLI → `tldr_app.remove_url`/`list_removed_urls` → `tldr_service.remove_url` and `removed_urls` persistence helpers (likely file-backed) corresponding to `removal_set_updated` and `removal_set_loaded` transitions.
- **Cache mode control:** UI/CLI → `tldr_app.get_cache_mode`/`set_cache_mode` → `cache_mode` module (enum + storage) supporting read/write gating for other modules, matching `cache_mode_read` and `cache_mode_updated` states.
- **Cache invalidation (range & date):** UI/CLI → `tldr_app.invalidate_cache_in_date_range`/`invalidate_cache_for_date` → `blob_store` delete helpers + `util.get_date_range`, with optional fetch of cached day JSON via `requests`. They exercise the `pathnames_built`, `deletion_loop`, and `per_url_cache_cleanup` states.

---
Subagent No. 4
==============

### Task
Detail the end-to-end call graph for every feature, annotating parameter flow and the state carried between steps.

### Result
Per-feature call graphs with state propagation:
- **Newsletter scraping**
  1. Client (CLI `scrape` or POST `/api/scrape`) collects `start_date`/`end_date` strings → `tldr_app.scrape_newsletters(start_date_text, end_date_text)`.
  2. `tldr_service.scrape_newsletters_in_date_range` invokes `_parse_date_range`, converting ISO strings into `datetime` objects while enforcing ordering and ≤31-day span (`state: date_range_validated`).
  3. Passing `(start_date, end_date)` to `newsletter_scraper.scrape_date_range` enters the per-day loop with `removed_urls = get_removed_urls()` providing the canonical removal set (`state: per_day_loop`).
  4. For each day `date`: compute `date_str = util.format_date_for_url(date)` then `_get_cached_day(date_str)` hits blob storage when `cache_mode.can_read()` (`state: cache_checked`).
     - Cache hit: hydrate `cached_articles`/`cached_issues`, canonicalize URLs via `util.canonicalize_url`, tag `article['fetched_via'] = "day_cache"`, and dedupe against `url_set` before appending to `all_articles` (`state: cache_hit → articles_deduped`).
     - Cache miss: iterate `newsletter_type in ("tech", "ai")` calling `_fetch_newsletter(date, newsletter_type)` which performs an HTTP GET to `https://tldr.tech/{newsletter_type}/{date_str}`, converts HTML to markdown, parses articles, stamps timing metadata, and returns `{articles, issue}` (`state: cache_miss → newsletters_fetched`). Articles are canonicalized, appended to `day_articles`, deduped into `all_articles`, and `others` counts fetches (`state: articles_normalized`).
  5. After processing a day with fresh data, sanitize `day_articles`/`day_issues`, then `_put_cached_day(date_str, sanitized_articles, sanitized_issues)` writes JSON via `blob_store.put_file` when `cache_mode.can_write()` (`state: day_cached`).
  6. Post-loop, mark each aggregated `article['removed'] = canonical_url in removed_urls` (`state: removed_flag_applied`), group by date, and call `_format_final_output` to produce timeline markdown plus stats. Response merges `output`, `articles_data` (with canonical URLs and metadata), `issues`, and cache statistics before returning to the client (`state: output_formatted`).
- **URL summarization**
  1. Client submits `url`, `cache_only`, `summary_effort` → `tldr_app.summarize_url` delegates to `tldr_service.summarize_url_content(url, cache_only, summary_effort)`.
  2. Service cleans `url`, raises on empty, canonicalizes via `util.canonicalize_url`, normalizes effort through `summarizer.normalize_summary_effort`, and forwards `canonical_url`, `cache_only`, `normalized_effort` (`state: url_canonicalized & effort_normalized`).
  3. `summarizer.summarize_url` is wrapped by `blob_cache.blob_cached(summary_blob_pathname)`, so the wrapper computes `pathname = summary_blob_pathname(canonical_url, summary_effort=normalized_effort)` and checks blob cache availability using `BLOB_STORE_BASE_URL` + `cache_mode` (`state: summary_lookup`).
     - Cache hit returns cached markdown immediately (`state: cache_hit → respond_with_blob_refs`).
     - Cache miss triggers the wrapped function: `url_to_markdown(canonical_url)` (also blob-cached) scrapes content:
       * Cache check on raw content using `_url_content_pathname`.
       * If miss, `_is_github_repo_url` directs GitHub README fetching (with token) or falls back to `scrape_url`, which tries `_scrape_with_curl_cffi` then `_scrape_with_jina_reader` before failing (`state: page_markdown_scraped`).
       * Markdown flows back, and decorators optionally cache raw markdown when writes allowed.
     - Template pipeline loads prompt via `_fetch_summarize_prompt` (memory cache → GitHub API) and `_insert_markdown_into_template`; `_call_llm` POSTs to OpenAI responses API with `input=prompt` and `reasoning.effort=normalized_effort`, then parses `output_text`/`choices` (`state: prompt_filled → llm_called`).
     - Resulting markdown bubbles up; the decorator writes summary markdown to blob storage when `cache_mode.can_write()` (`state: cache_written`).
  4. `tldr_service` assembles payload containing `summary_markdown`, `summary_blob_pathname`, optional `summary_blob_url = BLOB_STORE_BASE_URL/summary_blob_pathname`, plus `canonical_url` and `summary_effort`. Returning to `tldr_app`, the app wraps it with `success=True` and mirrors optional keys before responding (`state: respond_with_blob_refs`).
- **URL TLDR generation**
  1. Follows the same entry flow through `tldr_app.tldr_url` → `tldr_service.tldr_url_content` with identical canonicalization/normalization.
  2. Calls `summarizer.tldr_url`, which shares the blob cache flow but targets `tldr_blob_pathname` and loads `_fetch_tldr_prompt`, embedding markdown inside `<tldr this>` tags before `_call_llm` execution. The final payload surfaces `tldr_markdown`, TLDR blob metadata, `canonical_url`, and `summary_effort` mirroring the states recorded for the TLDR branch (`state: tldr_lookup → respond_with_blob_refs`).
- **Prompt inspection**
  1. Client hits CLI (`prompt`, `tldr-prompt`) or GET `/api/prompt`; `tldr_app.get_*_prompt_template` forwards to `tldr_service.fetch_*_prompt_template`.
  2. `summarizer._fetch_*_prompt` first checks `_PROMPT_CACHE`/`_TLDR_PROMPT_CACHE`; on miss it composes GitHub API URL, optionally injects `GITHUB_API_TOKEN`, fetches raw content, decodes base64 JSON responses if necessary, and seeds the in-memory cache before returning the text (`state: prompt_cache_checked → return_prompt`).
- **URL removal tracking**
  1. POST `/api/remove-url` or CLI `remove-url` calls `tldr_app.remove_url` → `tldr_service.remove_url(url)`.
  2. Service strips and validates scheme, canonicalizes, then `removed_urls.add_removed_url(canonical_url)` pulls existing set via HTTP GET (when base URL available), appends the URL, writes JSON with `blob_store.put_file`, and re-fetches to verify persistence. The canonical URL is bubbled back (`state: removal_set_updated`).
  3. Listing flows through `tldr_app.list_removed_urls` returning `list(removed_urls.get_removed_urls())`, which executes the same blob GET path and yields the set for response (`state: removal_set_loaded`).
- **Cache mode control**
  1. GET `/api/cache-mode` / CLI `cache-mode get` → `tldr_app.get_cache_mode` → `cache_mode.get_cache_mode()`, which respects `FORCE_CACHE_MODE`, consults in-memory `_cached_mode`, fetches blob text from `cache-mode.txt` if needed, validates into the `CacheMode` enum, and defaults to `READ_WRITE`. Value returns through the stack (`state: cache_mode_read`).
  2. POST `/api/cache-mode` / CLI `cache-mode set --mode=<value>` → `tldr_app.set_cache_mode(mode_str)` normalizes string, validates against enum, then `cache_mode.set_cache_mode(enum_value)` writes to blob via `put_file`, updates `_cached_mode`, and returns success (`state: cache_mode_updated`).
- **Cache invalidation (date range)**
  1. Client supplies `start_date`, `end_date` → `tldr_app.invalidate_cache_in_date_range` validates presence, parses to `datetime`, ensures ordering, and enumerates inclusive dates with `util.get_date_range` (`state: date_inputs_validated → date_range_enumerated`).
  2. Builds scrape day pathnames (`blob_store.build_scraped_day_cache_key`) and filters to existing entries via `blob_store.list_existing_entries`, which HEAD-checks each (`state: pathnames_built`).
  3. Iterates each existing pathname, calling `blob_store.delete_file` which issues a POST to `https://blob.vercel-storage.com/delete` (with RW token) and counts successes/failures, collecting error messages. Summary metrics emitted and returned (`state: deletion_loop → summary_compiled`).
- **Cache invalidation (single date)**
  1. `tldr_app.invalidate_cache_for_date(date_text)` ensures the date string exists, builds `day_cache_pathname`, and optionally fetches cached day JSON via HTTP GET to capture article URLs (`state: date_validated → day_blob_downloaded`).
  2. Extracted URLs are canonicalized (`util.canonicalize_url`) and normalized to blob path bases. For each canonical URL, it deletes raw content (`blob_store.delete_file(content_pathname)`) and summary files for every `SUMMARY_EFFORT_OPTIONS` value (e.g., `-summary-high`, etc.), counting successes/failures (`state: per_url_cache_cleanup`).
  3. Finally attempts to delete the day-level cache file, logs results, and returns counts plus a sample of deleted filenames (`state: day_cache_deleted → summary_compiled`).

Added inline comments in `tldr_app.py` capturing the summarize/TLDR and date invalidation flows for future readers.

---
