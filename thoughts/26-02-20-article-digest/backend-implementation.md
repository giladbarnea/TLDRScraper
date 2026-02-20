---
last_updated: 2026-02-20 13:03
---
# Backend Implementation Plan: Article Digest Feature

## Overview
Implement the backend for the multi-article digest feature following Group A specifications. The backend will fetch content for selected articles in parallel, build a multi-article digest prompt, call Gemini 3 Pro, and return the synthesized digest.

## Implementation Steps

### 1. API Route (`serve.py`)
**Add:** `POST /api/digest`

**Request body:**
```json
{
  "articles": [
    {"url": "...", "title": "...", "category": "..."},
    ...
  ],
  "effort": "low"  // optional, defaults to "low"
}
```

**Response:**
```json
{
  "success": true,
  "digest_id": "hash_of_urls_and_effort",
  "digest_markdown": "...",
  "article_count": 5,
  "included_urls": ["url1", "url2", ...],
  "skipped": [{"url": "url3", "reason": "Failed to fetch"}]
}
```

**Error handling:**
- ValueError → 400
- requests.RequestException → 502
- Generic → 500

### 2. App Layer (`tldr_app.py`)
**Add:** `generate_digest(articles, effort)`

Thin wrapper that:
- Delegates to `tldr_service.generate_digest()`
- Shapes response with `success: true`
- Returns formatted payload

### 3. Service Layer (`tldr_service.py`)
**Add:** `generate_digest(articles, effort)`

Core orchestration:
1. Validate inputs (articles array not empty, effort valid)
2. Canonicalize URLs via `util.canonicalize_url()`
3. Fetch content in parallel via ThreadPoolExecutor
   - Call `summarizer.url_to_markdown(url)` for each article
   - Handle partial failures gracefully
4. Build multi-article prompt
5. Call `summarizer._call_llm(prompt, effort)`
6. Return digest data

**Parallel fetching pattern:**
```python
with ThreadPoolExecutor(max_workers=5) as executor:
    future_to_article = {
        executor.submit(summarizer.url_to_markdown, article['url']): article
        for article in articles
    }

    for future in as_completed(future_to_article):
        article = future_to_article[future]
        try:
            markdown = future.result()
            # Process success
        except Exception as e:
            # Track failure
```

### 4. Prompt Engineering (`summarizer.py`)
**Add:** New digest prompt template

**Template location:** Store in `llm-templates` GitHub repo as `text/digest.md` (or hardcode initially)

**Prompt structure:**
```
{digest_template}

<articles>
<article url="{url1}" title="{title1}" source="{category1}">
{markdown_content_1_truncated}
</article>
<article url="{url2}" title="{title2}" source="{category2}">
{markdown_content_2_truncated}
</article>
...
</articles>
```

**Template instructions to Gemini:**
- Synthesize themes across articles
- Find connections and patterns
- Highlight key takeaways per article
- Attribute insights to source articles
- Format as markdown with headings, lists, links

**Token management (critical):**
- Truncate each article's markdown to ~3000 words before including
- Estimate total token count (rough: 1 word ≈ 1.3 tokens)
- If combined > 80K tokens, progressively truncate further
- MVP: simple truncation. Future: two-pass summarization

### 5. Storage Integration (Option A - MVP)
**Embed digests in `daily_cache` payloads**

Add optional `digest` field to payload:
```python
{
  "date": "2024-01-01",
  "articles": [...],
  "issues": [...],
  "digest": {  # NEW
    "id": "hash_of_urls_and_effort",
    "status": "available",
    "markdown": "...",
    "articleUrls": ["url1", "url2", ...],
    "generatedAt": "2024-01-01T12:00:00Z",
    "effort": "low",
    "errorMessage": None
  }
}
```

**Storage flow:**
1. Client initiates digest → backend generates
2. Backend returns digest to client
3. Client stores in daily payload for the most recent date in selection
4. Use existing `POST /api/storage/daily/{date}` endpoint
5. `mergePreservingLocalState` must preserve `digest` field (client-side concern)

### 6. Helper Functions

**Add to `summarizer.py`:**
```python
def _fetch_digest_prompt() -> str:
    """Fetch digest prompt template from GitHub or return hardcoded."""
    # Similar to _fetch_summary_prompt()
    # Cache in module global

def _truncate_markdown(markdown: str, max_words: int = 3000) -> str:
    """Truncate markdown to max words, preserving structure."""
    # Simple word-based truncation for MVP

def _build_digest_prompt(template: str, articles_with_content: list[dict]) -> str:
    """Build multi-article prompt from template and article data."""
    # articles_with_content: [{"url": ..., "title": ..., "category": ..., "markdown": ...}]

def _generate_digest_id(article_urls: list[str], effort: str) -> str:
    """Generate stable hash from sorted URLs + effort."""
    # Use hashlib.sha256
```

**Add to `tldr_service.py`:**
```python
def _fetch_articles_content_parallel(articles: list[dict]) -> tuple[list[dict], list[dict]]:
    """Fetch markdown for multiple articles in parallel.

    Returns: (successful_articles, failed_articles)
    successful: [{"url": ..., "title": ..., "category": ..., "markdown": ...}]
    failed: [{"url": ..., "reason": ...}]
    """
```

## Key Decisions

1. **Storage:** Option A (embed in daily_cache) for MVP
   - Zero schema changes
   - Reuses existing endpoints
   - Digestfits naturally with articles
   - Can migrate to dedicated table later if needed

2. **Content fetching:** Parallel via ThreadPoolExecutor
   - Reuses existing `summarizer.url_to_markdown()`
   - Handle partial failures (some URLs succeed, some fail)
   - Max 5 concurrent requests to avoid overwhelming

3. **Token management:** Simple truncation for MVP
   - Truncate each article to ~3000 words
   - Estimate combined tokens
   - Future: implement two-pass summarization if quality issues

4. **Prompt template:** Hardcode initially, extract to GitHub later
   - Faster iteration during development
   - Move to `llm-templates` repo once stable

5. **Digest ID:** Hash of sorted canonical URLs + effort
   - Enables cache hits on repeated selections
   - Immutable-by-default (regenerate = new ID)

## Testing Strategy

1. **Unit tests:** Test individual functions
   - `_truncate_markdown()` with various input lengths
   - `_generate_digest_id()` with same/different URL sets
   - `_build_digest_prompt()` with 2, 5, 10 articles

2. **Integration test:** End-to-end digest generation
   - Mock `url_to_markdown()` to avoid network calls
   - Test parallel fetching with partial failures
   - Verify prompt structure and LLM call

3. **Manual testing:** Real API calls
   - Start server with `uv run serve.py`
   - cURL POST to `/api/digest` with 3-5 articles
   - Verify markdown output quality
   - Test edge cases (all URLs fail, very long articles)

## Implementation Order

1. **Phase 1: Core digest logic**
   - Add helper functions to `summarizer.py`
   - Add `generate_digest()` to `tldr_service.py`
   - Add route to `serve.py`
   - Add thin wrapper to `tldr_app.py`

2. **Phase 2: Prompt engineering**
   - Hardcode digest prompt template
   - Test with 2-3 real articles
   - Iterate on template based on output quality

3. **Phase 3: Token management**
   - Implement `_truncate_markdown()`
   - Add token estimation logic
   - Test with large article sets (10+ articles)

4. **Phase 4: Error handling & polish**
   - Handle all edge cases
   - Add logging for debugging
   - Test with various failure scenarios

## Code Conventions to Follow

- Trust upstream inputs, fail early (no fallback-rich code)
- Use `util.resolve_env_var` for environment variables
- Use `uv run` for Python execution
- No abbreviations in variable/function names
- Add doctest examples to pure functions
- `util.log` when something is recoverable but wrong
- Prefer `import modulename` over `from modulename import function`

## Files to Modify

1. `/home/user/TLDRScraper/serve.py` - Add POST /api/digest route
2. `/home/user/TLDRScraper/tldr_app.py` - Add generate_digest() wrapper
3. `/home/user/TLDRScraper/tldr_service.py` - Add generate_digest() orchestration
4. `/home/user/TLDRScraper/summarizer.py` - Add digest helpers and prompt logic

## Files to Create

None (all changes are additions to existing files)

## Upstream/Downstream Concerns

1. **Client expects specific response shape** - Must match the documented response format
2. **Storage merge logic** - Client must handle `digest` field in merge (Group B concern)
3. **Zen lock** - Client must manage zen lock for digest overlay (Group B concern)
4. **Selection state** - Client provides article URLs (Group B concern)

## Success Criteria

- [ ] POST /api/digest endpoint accepts articles and effort
- [ ] Content fetched in parallel for all articles
- [ ] Partial failures handled gracefully
- [ ] Multi-article prompt constructed correctly
- [ ] Gemini 3 Pro generates coherent digest
- [ ] Response matches documented shape
- [ ] Token overflow prevented via truncation
- [ ] Manual testing with real articles succeeds
