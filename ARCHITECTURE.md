# TLDRScraper Architecture

## User Interactions → State Machines

### Newsletter scraping
- Entry via CLI `scrape` or POST `/api/scrape`.
- States: `input_pending → date_range_validated → per_day_loop`.
  - Each day: `cache_checked → (cache_hit → articles_deduped | cache_miss → newsletters_fetched → articles_normalized → day_cached)`.
- Exit states: `removed_flag_applied → output_formatted` with grouped articles, issue metadata, and stats.

### URL summarization
- Entry via CLI `summarize-url` or POST `/api/summarize-url`.
- States: `request_received → url_canonicalized → effort_normalized → summary_lookup`.
  - Hit: `cache_hit → respond_with_blob_refs`.
  - Miss: `page_markdown_scraped → prompt_filled → llm_called → cache_written → respond_with_blob_refs`.
- Canonical URL and summary effort persist throughout for cache addressing.

### URL TLDR generation
- Entry via CLI `tldr-url` or POST `/api/tldr-url`.
- Mirrors summarization but targets TLDR prompt & blobs: `request_received → url_canonicalized → effort_normalized → tldr_lookup → … → respond_with_blob_refs`.

### Prompt inspection
- Entry via CLI `prompt` / `tldr-prompt` or GET `/api/prompt`.
- States: `request_received → prompt_cache_checked → (memory_hit | github_fetch → memory_seeded) → return_prompt`.

### URL removal tracking
- Removal: `request_received → url_validated → canonicalized → removal_set_updated → success_response`.
- Listing: `request_received → removal_set_loaded → respond_list`.

### Cache mode control
- Get: `request_received → cache_mode_read → respond_mode`.
- Set: `request_received → mode_string_normalized → enum_validated → cache_mode_updated → respond_mode`.

### Cache invalidation
- Range: `request_received → date_inputs_validated → date_range_enumerated → pathnames_built → existing_entries_listed → deletion_loop → summary_compiled`.
- Single date: `request_received → date_validated → day_blob_downloaded → urls_extracted → per_url_cache_cleanup → day_cache_deleted → summary_compiled`.

## User Interactions → Call Graphs

### Newsletter scraping
1. UI/CLI → `tldr_app.scrape_newsletters(start_date, end_date)`.
2. `tldr_service.scrape_newsletters_in_date_range` → `_parse_date_range` (ISO check, ≤31 days).
3. `newsletter_scraper.scrape_date_range(start_date, end_date)` orchestrates per-day work:
   - Loads removal set via `removed_urls.get_removed_urls`.
   - For each date: `_get_cached_day` (blob GET when `cache_mode.can_read()`), or `_fetch_newsletter` (`requests.get` to `https://tldr.tech/{type}/{date}` → markdown via `MarkItDown` → structured parse).
   - Canonicalizes URLs with `util.canonicalize_url`, dedupes via `url_set`, annotates fetch provenance.
   - On fresh data: `_put_cached_day` writes JSON using `blob_store.put_file` if writes allowed.
4. Post-loop cleanup: flag removed URLs, group by date, format output, and return stats to caller.

### URL summarization
1. UI/CLI → `tldr_app.summarize_url(url, cache_only, summary_effort)`.
2. `tldr_service.summarize_url_content` trims input, canonicalizes via `util.canonicalize_url`, normalizes effort with `summarizer.normalize_summary_effort`.
3. `summarizer.summarize_url` (decorated by `blob_cache.blob_cached(summary_blob_pathname)`):
   - Computes pathname `summary_blob_pathname(canonical_url, summary_effort)`.
   - Cache check using `BLOB_STORE_BASE_URL` + `cache_mode`.
   - On miss: `url_to_markdown(canonical_url)` (also blob cached) scrapes content via `_fetch_github_readme` for GitHub repos or `scrape_url` (tries `_scrape_with_curl_cffi`, falls back to `_scrape_with_jina_reader`).
   - Loads summarize prompt with `_fetch_summarize_prompt` (in-memory cache → GitHub API).
   - Builds prompt via `_insert_markdown_into_template` and calls `_call_llm` (POST `https://api.openai.com/v1/responses`, `reasoning.effort=normalized_effort`).
   - Writes markdown back to blob store when `cache_mode.can_write()`.
4. `tldr_service` attaches blob metadata (`summary_blob_pathname`, optional base URL), canonical URL, and effort to the markdown; `tldr_app` wraps with `success=True` and returns.

### URL TLDR generation
- Same entry and service layers as summarization.
- `summarizer.tldr_url` shares blob cache logic but targets `tldr_blob_pathname` and `_fetch_tldr_prompt`, embedding markdown inside `<tldr this>` tags before `_call_llm` execution.
- Response payload surfaces TLDR markdown and blob references alongside canonical URL/effort.

### Prompt inspection
1. UI/CLI → `tldr_app.get_summarize_prompt_template` or `get_tldr_prompt_template`.
2. `tldr_service.fetch_*_prompt_template` → `summarizer._fetch_*_prompt`.
3. Prompt helper checks `_PROMPT_CACHE`/`_TLDR_PROMPT_CACHE`, otherwise fetches GitHub content (optionally using `GITHUB_API_TOKEN`) and caches it in memory before returning plain text.

### URL removal tracking
- Removal: UI/CLI → `tldr_app.remove_url` → `tldr_service.remove_url` → `removed_urls.add_removed_url` (read current set via blob GET, append canonical URL, persist through `blob_store.put_file`, verify by re-reading).
- Listing: UI/CLI → `tldr_app.list_removed_urls` → `_get_removed_urls` alias → `removed_urls.get_removed_urls` (blob GET, parse JSON list → set).

### Cache mode control
- Get: UI/CLI → `tldr_app.get_cache_mode` → `cache_mode.get_cache_mode` (respect `FORCE_CACHE_MODE`, consult `_cached_mode`, otherwise GET `cache-mode.txt` via blob and coerce into `CacheMode`).
- Set: UI/CLI → `tldr_app.set_cache_mode` (normalize string → enum) → `cache_mode.set_cache_mode` (write enum value using `blob_store.put_file`, update `_cached_mode`).

### Cache invalidation
- Date range: UI/CLI → `tldr_app.invalidate_cache_in_date_range` (ISO parsing, date sequence) → build `scrape-day-YYYY-MM-DD.json` keys with `blob_store.build_scraped_day_cache_key` → filter existing entries through `blob_store.list_existing_entries` → delete each via `blob_store.delete_file` (POST `/delete` API) while collecting success/failure counts → return summary.
- Single date: UI/CLI → `tldr_app.invalidate_cache_for_date` → best-effort GET of cached day JSON → derive canonical URLs, convert to blob path bases → delete raw content and per-effort summaries (`SUMMARY_EFFORT_OPTIONS`) with `blob_store.delete_file` → delete the day aggregate file and report counts/sample filenames.

## Data & External Services
- **Blob storage:** Vercel Blob hosts day-level scrapes, URL markdown, summaries/TLDRs, removed URLs, and cache mode flag. Access controlled via `BLOB_STORE_BASE_URL` and `BLOB_READ_WRITE_TOKEN`.
- **OpenAI Responses API:** `_call_llm` posts prompts with configurable reasoning effort.
- **GitHub API:** Prompt templates are fetched from `giladbarnea/llm-templates` via authenticated or anonymous requests.
- **TLDR newsletters:** `_fetch_newsletter` scrapes `https://tldr.tech/<type>/<date>`.
- **Jina reader & curl_cffi:** fallback scrapers for arbitrary article URLs.

## URL & Article State Notes
- Canonical URLs generated by `util.canonicalize_url` feed every cache key, removal flag, and cleanup routine, ensuring deduplication across newsletter scrapes and summary/TLDR outputs.
- Article lifecycle: scraped (network/day cache) → canonicalized → deduped → removal flag applied → returned with metadata → eligible for per-date invalidation which clears both raw content (`normalize_url_to_pathname`) and derivative summaries/TLDRs derived from the same canonical base.
