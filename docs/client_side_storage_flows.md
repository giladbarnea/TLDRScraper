# Client-Side Local Storage Architecture

The TLDR scraper now runs as a stateless pipeline: the browser is the only
persistent store, while the Python backend simply proxies scrape and LLM
requests. This document captures the current implementation so new changes can
stay aligned with the live system.

## Architecture overview

- **Browser-owned persistence** – Newsletter payloads, article metadata,
  summary/TLDR results, and read state all live in `localStorage`. Every user
  action mutates in-memory state first, mirrors that change to disk, and renders
  directly from the hydrated snapshot.
- **Stateless backend** – Flask only exposes `/`, `POST /api/scrape`, `POST
  /api/summarize-url`, `POST /api/tldr-url`, and `GET /api/prompt`. Each request
  forwards to `tldr_app` → `tldr_service` → the newsletter scraper or
  summarizer helpers without touching any cache store.
- **Deterministic contracts** – The frontend expects canonicalized URLs, issue
  metadata, and article lists with `removed` hints. All status flags are managed
  in the browser and never echoed by the server.

## Client implementation

### Persistent keys and shapes

| Key | Shape | Purpose |
| --- | ----- | ------- |
| `tldr:scrapes:<ISO-date>` | `{ cachedAt: ISO-string \| null, issues: Issue[], articles: Article[] }` | Browser-owned payload for a single day. |
| `tldr-read-issues` | `{ [issueKey: string]: true }` | Tracks collapsed “read” issues so they stay hidden across sessions. |

#### `Article`

```
type Article = {
    url: string;
    title: string;
    issueDate: string;          // ISO date for the owning day
    category: string;           // e.g. "TLDR Tech"
    section: string | null;     // section title, if present
    sectionEmoji: string | null;
    sectionOrder: number | null;
    newsletterType: string | null; // raw TLDR section type
    removed: boolean;
    summary: {
        status: 'unknown' | 'creating' | 'available' | 'error';
        markdown: string;
        effort: 'minimal' | 'low' | 'medium' | 'high';
        checkedAt: string | null;
        errorMessage: string | null;
    };
    tldr: {
        status: 'unknown' | 'creating' | 'available' | 'error';
        markdown: string;
        effort: 'minimal' | 'low' | 'medium' | 'high';
        checkedAt: string | null;
        errorMessage: string | null;
    };
    read: {
        isRead: boolean;
        markedAt: string | null;
    };
};
```

#### `Issue`

```
type Issue = {
    date: string | null;            // ISO date for the issue
    category: string;               // TLDR Tech / TLDR AI / etc.
    newsletterType: string | null;  // tech, ai, etc.
    title: string | null;
    subtitle: string | null;
    sections: Array<{
        order: number | null;
        title: string | null;
        emoji: string | null;
    }>;
};
```

### Storage helpers (`ClientStorage`)

`ClientStorage` (see `templates/index.html`) wraps all `localStorage` access:

- `readDay(date)` → parse `tldr:scrapes:<date>` into the canonical Article/Issue
  shape.
- `writeDay(date, payload)` → persist a normalized snapshot back to storage.
- `mergeDay(date, payload)` → combine a fresh scrape with stored summaries/TLDRs
  so repeat visits keep prior results.
- `hasDay(date)` → boolean existence check used before hitting the network.
- `updateArticle(date, url, updater)` → transactional updater that applies a
  mutation function, clones the result, and rewrites the owning day.

### Hydration and rendering (`ClientHydration`)

`buildDailyPayloadsFromScrape` normalizes live `/api/scrape` responses,
canonicalizes URLs, and seeds new articles with `unknown` summary/TLDR states.
When merges find prior entries, the stored summary/TLDR/read data wins so state
persists across fetches.

`renderPayloads` rebuilds the Whitey reading surface: it prints stats, renders
the Markdown-like layout, indexes payload metadata, applies stored article
state (including error/loading flags), and triggers downstream flows like
summary/TLDR prefetch.

`hydrateRangeFromStore` pulls a date range entirely from `localStorage` so the
UI can render instantly when all days are cached.

### Article ordering and read tracking (`ArticleStateTracks`)

Cards stay ordered by unread → read via `sortArticlesByState`. `markArticleAsRead`
updates DOM classes, resorts the list, and persists `{ isRead: true,
markedAt: now }` with `ClientStorage.updateArticle`.

### Summary effort controls (`SummaryEffortSelector`)

Each card owns a reasoning level dropdown. Selecting a new effort:

1. Clears any cached summary markup and inline expander.
2. Resets the Summary button to "Summarize".
3. Stores the effort in `data-summary-effort` and writes it to storage so future
   fetches use the same effort value.
4. Immediately triggers a fresh summary request by programmatically clicking the
   expand button.

### Summary flow (`SummaryDelivery`)

- `loadSummaries` walks the newest two newsletter days and posts to
  `/api/summarize-url` with `summary_effort` from each card. Because the backend
  is stateless, these requests always produce fresh summaries that are then
  cached in `localStorage`.
- `bindSummaryExpansion` intercepts clicks on card titles or the "Summarize"
  button. It toggles cached summaries, injects new `div.inline-summary`
  elements, and wraps all state changes in `ClientStorage.updateArticle` so
  success, error, and in-flight flags persist. Errors reset the button to
  "Summarize" with a retry affordance.
- Successful fetches mark the article as read and surface a copy-to-clipboard
  action.

### TLDR flow (`TldrDelivery`)

`loadTldrs` mirrors `loadSummaries`, prefilling TLDRs for the most recent
issues. `bindTldrExpansion` owns manual TLDR toggles: it draws
`div.inline-tldr`, updates storage, and handles retries. Both success and error
paths keep `tldr.status` synchronized with the UI.

### Issue-level read state (`IssueDayReadState` and `IssueCollapseManager`)

Entire issues can be collapsed into a "Read Issues" section. `IssueDayReadState`
serializes the `date-category` issue key into `tldr-read-issues`. When an issue
is marked read:

1. The header container moves into the collapsed section.
2. Subsequent hydrations hide the issue immediately.
3. Clicking the issue again expands it in place without disturbing the stored
state.

`IssueCollapseManager` centralizes the DOM bookkeeping so header buttons,
chevrons, and collapsed cards all act consistently.

### Additional client systems

- **SummaryClipboard** – Formats YAML front matter + markdown and copies it to
  the clipboard with toast feedback.
- **ScrapeIntake** – Validates date ranges, hydrates from cache when possible,
  calls `/api/scrape` for misses, and pipes responses through `ClientStorage`.
- **Debug panel** – Overrides `console.log`/`console.error` to surface messages
  in a collapsible UI panel for easier QA.

## Backend implementation

### HTTP surface (`serve.py`)

| Route | Method | Handler | Notes |
| ----- | ------ | ------- | ----- |
| `/` | GET | `index` | Serves `templates/index.html` |
| `/api/scrape` | POST | `scrape_newsletters_in_date_range` | Validates JSON body and proxies to `tldr_app.scrape_newsletters`. |
| `/api/prompt` | GET | `get_summarize_prompt_template` | Returns the summarize prompt as plain text. |
| `/api/summarize-url` | POST | `summarize_url` | Expects `{"url", "summary_effort"}` and forwards to `tldr_app.summarize_url`. |
| `/api/tldr-url` | POST | `tldr_url` | Expects `{"url", "summary_effort"}` and forwards to `tldr_app.tldr_url`. |

Handlers log failures via `util.log` and rely on upstream validation. The API is
strict: missing JSON fields trigger 400s; network issues bubble up as 5xx.

### Application façade (`tldr_app.py`)

`tldr_app` is a thin wrapper that adapts service responses into the exact JSON
shape the frontend expects:

- `scrape_newsletters` – forwards to `tldr_service.scrape_newsletters_in_date_range`.
- `summarize_url` / `tldr_url` – return `{ success: True, summary_markdown?, tldr_markdown?, canonical_url?, summary_effort? }`.
- Prompt helpers simply expose the templates loaded by the service.

### Service layer (`tldr_service.py`)

- `_parse_date_range` enforces ISO strings, range ordering, and a 31-day cap.
- `scrape_newsletters_in_date_range` logs start/end, delegates to
  `newsletter_scraper.scrape_date_range`, and returns the scraper payload as-is.
- `summarize_url_content` / `tldr_url_content` normalize URLs, normalize effort,
  call `summarizer`, and return canonical URLs with markdown output.
- `fetch_*_prompt_template` lazily load prompts through the summarizer helpers.

### Newsletter scraping (`newsletter_scraper.py`)

`scrape_date_range` iterates TLDR newsletter types (tech + ai) for each day in
the requested range:

1. `_collect_newsletters_for_date` fetches each newsletter, parses headings and
   section structure into `NewsletterIssue`, and deduplicates articles by
   canonical URL.
2. Articles record timing metadata (`timing_*_ms`) for debugging and always set
   `removed` to `False` unless the source indicated otherwise.
3. `_build_scrape_response` composes:
   - `articles`: flattened list with category, section, and removal hints.
   - `issues`: sorted issue metadata for rendering.
   - `stats`: totals plus `debug_logs` (mirroring `util.LOGS`).
   - `output`: Markdown summary of the scrape used when copying the newsletter.

No caching hooks remain—each request re-scrapes the TLDR site.

### Summarizer pipeline (`summarizer.py`)

- Fetches page content with `curl_cffi` and falls back to the r.jina.ai reader.
- Converts HTML to Markdown via `markitdown`. GitHub repository URLs fetch the
  README directly using the GitHub API when possible.
- Loads summarize/TLDR prompts from `giladbarnea/llm-templates`, caching the
  raw text in process globals.
- Calls the OpenAI Responses API (`gpt-5`) with reasoning effort derived from the
  request. `_call_llm` accepts multiple response shapes and always returns a
  string.

## Request and response contracts

### `POST /api/scrape`

Request:

```
{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }
```

Response (success):

```
{
  "success": true,
  "articles": [
    {
      "url": "https://…",
      "title": "Example (2 minute read)",
      "date": "2024-05-01",
      "category": "TLDR Tech",
      "removed": false,
      "section_title": "Headlines",
      "section_emoji": "🚀",
      "section_order": 1,
      "newsletter_type": "tech"
    },
    …
  ],
  "issues": [Issue, …],
  "stats": {
    "total_articles": number,
    "unique_urls": number,
    "dates_processed": number,
    "dates_with_content": number,
    "network_fetches": number,
    "cache_mode": "read_write",
    "debug_logs": string[]
  ],
  "output": "# TLDR Newsletter Articles …"
}
```

### `POST /api/summarize-url`

Request:

```
{ "url": "https://…", "summary_effort": "minimal" | "low" | "medium" | "high" }
```

Response (success):

```
{
  "success": true,
  "summary_markdown": "…",
  "canonical_url": "https://…",
  "summary_effort": "low"
}
```

### `POST /api/tldr-url`

Same shape as `/api/summarize-url`, but the response field is `tldr_markdown`.

### `GET /api/prompt`

Returns the summarize prompt as plain text for inspection.

## Operational notes

- Source `./setup.sh` to install dependencies (`ensure_uv`) and set up helper
  functions.
- Use `start_server_and_watchdog` to launch the Flask app with the watchdog
  health checker, `print_server_and_watchdog_pids` to verify processes, and
  `kill_server_and_watchdog` for cleanup.
- Exercise the endpoints with `curl` (see `setup.sh` comments) to validate flows
  after code changes.
