---
last_updated: 2026-02-20 07:52
---
# Analysis: Summarizer & Gemini Integration

## Overview
The summarizer module provides URL-to-summary functionality with a fallback chain for content extraction (curl_cffi → Jina Reader → Firecrawl), HTML-to-markdown conversion, LLM prompt construction from GitHub template, and Gemini API calls with configurable reasoning effort levels.

## Entry Points

1. `/home/user/TLDRScraper/summarizer.py:286-304` - `summarize_url()` - Main public API
2. `/home/user/TLDRScraper/tldr_service.py:313-344` - `summarize_url_content()` - Service layer wrapper
3. `/home/user/TLDRScraper/tldr_app.py:29-54` - `summarize_url()` - App layer endpoint

## Core Implementation

### 1. Content Extraction Chain (`/home/user/TLDRScraper/summarizer.py:161-204`)

**scrape_url(url, timeout=10)**
- **Responsibilities**: Fetch raw HTML from URL using fallback chain
- **Fallback Chain**:
  1. `curl_cffi` (lines 65-84): Browser impersonation with Chrome 131, 10s timeout
  2. `jina_reader` (lines 87-104): r.jina.ai service for reader mode extraction, 10s timeout
  3. `firecrawl` (lines 107-157): Full browser rendering via Firecrawl API, 60s timeout (conditional on FIRECRAWL_API_KEY)
- **Error Handling**: Tries all methods sequentially, collects errors, re-raises last HTTPError or RuntimeError if all fail
- **Retry**: Decorated with `@util.retry()` for transient failures
- **Output**: `requests.Response` object with HTML content

**Special Case: GitHub Repos (`/home/user/TLDRScraper/summarizer.py:206-268`)**
- **_fetch_github_readme(url)**: Detects GitHub repo URLs, fetches raw README.md from main/master branch
- **Authentication**: Uses GITHUB_API_TOKEN if available
- **Fallback**: If raw fetch fails, falls back to scrape_url

### 2. HTML to Markdown Conversion (`/home/user/TLDRScraper/summarizer.py:271-283`)

**url_to_markdown(url)**
- **Configuration** (lines 16-22): Global html2text instance configured for optimal markdown conversion
  - `body_width=0` - No line wrapping
  - `unicode_snob=True` - Unicode over ASCII
  - `ignore_images=True` - Text only
  - `protect_links=True` - Don't wrap URLs
  - `single_line_break=True` - Single newlines
- **Flow**:
  1. Check if GitHub repo URL → call `_fetch_github_readme()`
  2. Otherwise → call `scrape_url()` → convert HTML to markdown via `h.handle(response.text)`
- **Output**: Markdown string

### 3. Prompt Construction (`/home/user/TLDRScraper/summarizer.py:360-373`)

**_fetch_summary_prompt()**
- **Source**: GitHub API - `giladbarnea/llm-templates/main/text/tldr.md`
- **Caching**: In-memory cache via `_SUMMARY_PROMPT_CACHE` module global (line 24)
- **Template Content**:
  - Aggressive TLDR with executive-summary tone
  - Markdown formatting requirements (headings, bold, italics, lists)
  - Style constraints: no nested lists, 1-2 heading levels, include links, preserve author's voice
  - Start with bottom line, then body
- **Authentication**: Uses GITHUB_API_TOKEN if available, falls back to unauthenticated
- **Error Handling**: Tries Accept header, then base64 decode from JSON response, then retry without auth token
- **Prompt Assembly** (line 301): `"{template}\n\n<tldr this>\n{markdown}/n</tldr this>"`
  - Note: Typo in code - `/n` instead of `\n` before closing tag

### 4. LLM API Call (`/home/user/TLDRScraper/summarizer.py:394-441`)

**_call_llm(prompt, summarize_effort=DEFAULT_SUMMARY_EFFORT, model=DEFAULT_MODEL)**
- **API Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- **Model**: `gemini-3-pro-preview` (line 28)
- **Authentication**: `x-goog-api-key` header from GEMINI_API_KEY env var
- **Timeout**: 600 seconds (10 minutes) - line 420
- **Request Structure** (lines 409-418):
  ```json
  {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
      "thinkingConfig": {
        "thinkingLevel": "low" | "high"
      }
    }
  }
  ```
- **Effort Levels** (lines 26, 376-391):
  - Input: "minimal" | "low" | "medium" | "high"
  - Mapping: minimal/low → "low", medium/high → "high"
  - Default: "low"
- **Response Parsing** (lines 424-440):
  1. Extract `candidates` array (raises if empty)
  2. Extract `content.parts` from first candidate
  3. Collect all `text` values from parts
  4. Join with newlines
  5. Raise if no text found
- **Error Handling**: Raises RuntimeError for missing candidates or text; requests.HTTPError for API errors

### 5. Service & App Layers

**tldr_service.summarize_url_content() (`/home/user/TLDRScraper/tldr_service.py:313-344`)**
- **Preprocessing**: URL validation, canonicalization via `util.canonicalize_url()`
- **Error Handling**: Catches `requests.RequestException`, logs, re-raises
- **Output**: Dict with `summary_markdown`, `canonical_url`, `summarize_effort`

**tldr_app.summarize_url() (`/home/user/TLDRScraper/tldr_app.py:29-54`)**
- **Thin wrapper**: Calls service layer, wraps response with `success: true`
- **Output**: Dict with `success`, `summary_markdown`, `canonical_url`, `summarize_effort`

## Data Flow

1. HTTP request → `tldr_app.summarize_url(url, effort, model)` (line 29)
2. → `tldr_service.summarize_url_content()` (line 313)
   - URL validation & canonicalization
3. → `summarizer.summarize_url()` (line 286)
4. → `summarizer.url_to_markdown()` (line 271)
   - GitHub repo check → `_fetch_github_readme()` (lines 206-268)
   - Otherwise → `scrape_url()` (lines 161-204)
     - Fallback chain: curl_cffi → jina_reader → firecrawl
   - HTML → markdown via `h.handle()`
5. → `summarizer._fetch_summary_prompt()` (line 300)
   - GitHub API fetch with in-memory caching
6. → Prompt assembly: `"{template}\n\n<tldr this>\n{markdown}/n</tldr this>"` (line 301)
7. → `summarizer._call_llm(prompt, effort, model)` (line 302)
   - Effort normalization & mapping to thinking level
   - Gemini API POST with 600s timeout
   - Response parsing & text extraction
8. ← Summary markdown string propagates back through layers

## Key Patterns

- **Fallback Chain**: Content extraction tries multiple methods until one succeeds (`scrape_url`)
- **Retry Pattern**: `@util.retry()` decorator on `scrape_url` for resilience
- **In-Memory Caching**: Prompt template cached in module global to avoid repeated GitHub API calls
- **URL Canonicalization**: Service layer normalizes URLs before processing
- **Error Propagation**: Errors bubble up with logging at service layer
- **Separation of Concerns**: App layer (thin wrapper) → Service layer (validation/logging) → Core logic (summarizer)

## Configuration

- **Models**: Default `gemini-3-pro-preview` (line 28)
- **Effort Levels**: "minimal" | "low" (default) | "medium" | "high" (line 26-27)
- **Timeouts**:
  - Scraping: 10s (curl_cffi, jina), 60s (firecrawl) - lines 66, 87, 107, 178
  - GitHub fetch: 10s - lines 229, 248, 330
  - Gemini API: 600s - line 420
- **Retry**: Configured via `@util.retry()` decorator (parameters in util.py)
- **Environment Variables**:
  - `GEMINI_API_KEY` (required) - line 396
  - `FIRECRAWL_API_KEY` (optional) - line 108
  - `GITHUB_API_TOKEN` (optional) - lines 220, 326

## Error Handling

- **Missing API Key**: Raises RuntimeError "GEMINI_API_KEY not set" (line 398)
- **Empty Prompt**: Raises ValueError "Prompt is empty" (line 400)
- **Scraping Failures**: Logs all method failures, re-raises last HTTPError or RuntimeError (lines 186-203)
- **GitHub Fetch Failures**: Tries main branch, falls back to master, then scrape_url (lines 238-268)
- **Gemini API Errors**:
  - HTTP errors raised via `resp.raise_for_status()` (line 421)
  - Missing candidates: RuntimeError with response data (line 426)
  - Missing text: RuntimeError with response data (line 440)
- **Service Layer**: Catches RequestException, logs with `exc_info=True`, re-raises (lines 332-338)

## Token/Length Limits & Chunking

**No Explicit Limits Found**:
- No token counting or truncation logic in codebase
- No chunking implementation for large content
- Gemini API request has no `maxOutputTokens` or content length limits configured
- 10-minute timeout is the only constraint (line 420)

**Potential Issues**:
- Large articles could exceed Gemini's context window
- No handling for oversized markdown (e.g., very long articles, documentation sites)
- No token counting before API call
- Prompt template + full markdown sent as-is

**Current Behavior**:
- If content too large, Gemini API likely returns error or truncates silently
- No graceful degradation for oversized content

## Multi-Article Digest Considerations

### What Would Need to Change

**1. Prompt Construction**:
- Current: Single `<tldr this>{markdown}</tldr this>` block (line 301)
- Needed: Multiple article blocks with metadata (title, URL, source)
- Example structure:
  ```
  {template}

  <articles>
  <article url="{url1}" title="{title1}">
  {markdown1}
  </article>
  <article url="{url2}" title="{title2}">
  {markdown2}
  </article>
  </articles>
  ```

**2. Template Update**:
- Current template is single-article focused ("TLDR the given content")
- Need new template for multi-article digests:
  - Cross-article themes and connections
  - Grouped/comparative summaries
  - Metadata handling (source attribution)

**3. Token Management** (CRITICAL):
- **Must implement**: Token counting for combined content
- **Must handle**: Content exceeding context window
- **Options**:
  - Pre-truncate each article markdown
  - Intelligent summarization in multiple passes
  - Chunking with aggregation
  - Article selection/prioritization

**4. New Function Signature**:
```python
def summarize_multiple_urls(
    articles: list[dict],  # [{"url": str, "title": str, "markdown": str | None}, ...]
    summarize_effort: str = DEFAULT_SUMMARY_EFFORT,
    model: str = DEFAULT_MODEL,
) -> str:
    """Generate combined digest from multiple articles."""
```

**5. Content Fetching**:
- Current `url_to_markdown()` could be reused for each URL
- Consider parallel fetching for multiple URLs (already have ThreadPoolExecutor in tldr_service)
- Error handling: partial failures (some URLs succeed, some fail)

**6. Caching Strategy**:
- Cache individual article markdown to avoid re-scraping
- Cache multi-article digests by article set hash

### Reusable Components

**Can Reuse As-Is**:
- `url_to_markdown()` - Content extraction for each URL
- `_call_llm()` - Gemini API call (just needs different prompt)
- `normalize_summarize_effort()` - Effort level handling
- `scrape_url()` - Fallback chain
- Error handling patterns
- Retry logic

**Need Modification**:
- Prompt construction (multi-article structure)
- Template fetching (new template or parameterized)
- Response structure (may want article-level metadata)

### Implementation Approach

**Option 1: Simple Concatenation**
- Fetch markdown for each URL
- Concatenate with delimiters
- Use modified prompt template
- Call `_call_llm()` with combined content
- **Risk**: Token overflow, no chunking

**Option 2: Two-Pass Summarization**
- First pass: Summarize each article individually (reuse existing logic)
- Second pass: Meta-summary of all summaries
- **Benefit**: Token control, graceful degradation
- **Cost**: 2x API calls

**Option 3: Intelligent Aggregation**
- Pre-summarize or truncate long articles
- Build structured prompt with article metadata
- Single LLM call for digest
- **Benefit**: Balanced token usage, single coherent output
- **Complexity**: Needs token counting, truncation logic

### Missing Pieces for Production

1. **Token Counting**: No library imported for Gemini tokenization
2. **Content Truncation**: No logic to trim oversized markdown
3. **Error Recovery**: Partial failure handling (some articles fail to fetch)
4. **Prompt Engineering**: New template for multi-article context
5. **Testing**: Need to verify Gemini 3 Pro Preview handles multi-article well
6. **Metadata Preservation**: Track which parts of digest came from which URL

## Notes

- **Typo in Prompt Assembly**: Line 301 has `/n` instead of `\n` before closing tag (likely harmless)
- **No Output Length Control**: Gemini's natural response length is trusted
- **Browser Rendering Available**: Firecrawl provides JavaScript-rendered content for complex sites
- **Thinking Level Binary**: Maps 4 effort levels to just 2 Gemini thinking levels
- **Module Structure Clean**: Clear separation between extraction (scraping), transformation (markdown), and LLM call
