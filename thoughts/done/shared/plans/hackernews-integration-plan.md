---
last-updated: 2025-10-27 23:12, 2dd2aac
---

# HackerNews Integration Implementation Plan

## Overview

Add HackerNews as a newsletter source using the `haxor` Python library. This integration requires minor modifications to the existing NewsletterAdapter abstraction to support API-based sources that don't follow date-specific URL patterns.

## Current State Analysis

### What Exists
- `newsletter_adapter.py` - Abstract base class with template method pattern
- `newsletter_config.py` - Configuration schema and registry (NEWSLETTER_CONFIGS)
- `newsletter_scraper.py` - Factory pattern and orchestration
- `tldr_adapter.py` - Reference implementation for HTML-based sources
- `newsletter_merger.py` - Source-agnostic response merging

### What's Missing
- Support for API-based sources (vs HTML scraping)
- HackerNewsAdapter implementation
- HackerNews source configuration
- Factory registration for HackerNews

### Key Constraints
- Must maintain backward compatibility with existing TLDR sources
- Must follow standard response format (articles + issues)
- HackerNews API only provides "latest" feeds, not historical archives
- Need to filter client-side by submission_time for date ranges

## Desired End State

A fully functional HackerNews source that:
- Fetches stories from HN API using haxor library
- Filters stories by date to match scrape_date_range behavior
- Returns standardized response format compatible with existing UI
- Supports all HN story types: top, new, ask, show, job
- Can be enabled/disabled via sources parameter in /api/scrape

### Verification
```bash
# Start server
uv run python3 serve.py

# Test HackerNews alone
curl -X POST http://localhost:5001/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-10-27", "end_date": "2025-10-27", "sources": ["hackernews"]}'

# Test HackerNews with TLDR
curl -X POST http://localhost:5001/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-10-27", "end_date": "2025-10-27", "sources": ["tldr_ai", "tldr_tech", "hackernews"]}'

# Verify response has:
# - articles with source_id="hackernews"
# - articles with category="HN Top", "HN New", etc.
# - proper date filtering
```

## What We're NOT Doing

- Historical HackerNews data scraping (API doesn't support it)
- HackerNews comment scraping (only top-level stories)
- Custom HackerNews authentication (API is public)
- Caching HackerNews responses (defer to future enhancement)
- Issue metadata for HackerNews (no newsletter-style issues)
- Section support for HackerNews (no newsletter-style sections)

## Implementation Approach

Use **Template Method Override** pattern: Make `scrape_date()` overridable in the base class, allowing HackerNewsAdapter to implement its own API-based fetching and filtering logic while maintaining the standard response format.

---

## Phase 1: Modify NewsletterAdapter Abstraction

### Overview
Make the NewsletterAdapter more flexible to support both HTML-based and API-based sources.

### Changes Required

#### 1. NewsletterAdapter Base Class
**File**: `newsletter_adapter.py`

**Changes**:
- Make abstract methods optional (not strictly abstract)
- Add default implementations that raise NotImplementedError
- Document that `scrape_date()` can be overridden for custom workflows

```python
# Around line 35-78, modify abstract methods:

# OLD (strict abstract):
@abstractmethod
def fetch_issue(self, date: str, newsletter_type: str) -> str | None:
    pass

# NEW (optional override):
def fetch_issue(self, date: str, newsletter_type: str) -> str | None:
    """Fetch raw HTML for a specific issue.

    Override this method for HTML-based sources.
    For API-based sources, override scrape_date() instead.

    Args:
        date: Date string in format used by source
        newsletter_type: Type/category within source (e.g., "tech", "ai")

    Returns:
        HTML content as string, or None if issue not found
    """
    raise NotImplementedError(
        f"{self.__class__.__name__} must implement fetch_issue() or override scrape_date()"
    )

# Same pattern for parse_articles and extract_issue_metadata
```

Add documentation to `scrape_date()`:
```python
# Around line 80, update docstring:

def scrape_date(self, date: str) -> dict:
    """Template method - orchestrates fetch + parse + normalize.

    This default implementation follows the HTML scraping workflow:
    1. Fetch HTML for each type configured for this source
    2. Convert HTML to markdown
    3. Parse articles and extract metadata
    4. Normalize response with source_id

    Subclasses can override this entire method for different workflows
    (e.g., API-based sources that don't use HTML conversion).

    Args:
        date: Date string to scrape

    Returns:
        Normalized response dictionary with source_id, articles, and issues
    """
    # ... existing implementation
```

### Success Criteria

#### Automated Verification
- [ ] Python syntax check: `uv run python3 -m py_compile newsletter_adapter.py`
- [ ] TLDRAdapter still works (doesn't override scrape_date): `uv run python3 -c "from tldr_adapter import TLDRAdapter; from newsletter_config import NEWSLETTER_CONFIGS; adapter = TLDRAdapter(NEWSLETTER_CONFIGS['tldr_tech']); print('TLDRAdapter loads successfully')"`

#### Manual Verification
- [ ] Existing TLDR scraping still works via /api/scrape endpoint

**Implementation Note**: After completing this phase and automated verification passes, pause for manual confirmation that TLDR scraping works before proceeding.

---

## Phase 2: Create HackerNews Source Configuration

### Overview
Register HackerNews as a source in the configuration system.

### Changes Required

#### 1. Add HackerNews Config
**File**: `newsletter_config.py`

**Changes**: Add new config entry to NEWSLETTER_CONFIGS dict (around line 58)

```python
# After tldr_ai config, add:

"hackernews": NewsletterSourceConfig(
    source_id="hackernews",
    display_name="Hacker News",
    base_url="https://hacker-news.firebaseio.com/v0",
    url_pattern="",  # Not used for API-based sources
    types=["top", "new", "ask", "show"],  # Start with 4 types, can add "job" later
    user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
    article_pattern="",  # Not used for API-based sources
    section_emoji_enabled=False,  # HackerNews doesn't have sections
    category_display_names={
        "top": "HN Top",
        "new": "HN New",
        "ask": "HN Ask",
        "show": "HN Show",
    },
    sort_order=3,  # After TLDR AI (1) and TLDR Tech (2)
),
```

### Success Criteria

#### Automated Verification
- [ ] Python syntax check: `uv run python3 -m py_compile newsletter_config.py`
- [ ] Config loads correctly: `uv run python3 -c "from newsletter_config import NEWSLETTER_CONFIGS; assert 'hackernews' in NEWSLETTER_CONFIGS; print('HackerNews config registered')"`
- [ ] Config has required fields: `uv run python3 -c "from newsletter_config import NEWSLETTER_CONFIGS; hn = NEWSLETTER_CONFIGS['hackernews']; assert hn.source_id == 'hackernews'; assert 'top' in hn.types; print('Config valid')"`

#### Manual Verification
- [ ] Config values are sensible (display names, sort order)

---

## Phase 3: Implement HackerNewsAdapter

### Overview
Create the HackerNewsAdapter that fetches stories from the HN API and converts them to the standard response format.

### Changes Required

#### 1. Create New File
**File**: `hackernews_adapter.py`

**Changes**: Create new file with HackerNewsAdapter class

```python
"""
HackerNews adapter implementation using the haxor library.

This adapter implements the NewsletterAdapter interface for HackerNews,
using the HackerNews API instead of HTML scraping.
"""

import asyncio
import logging
from datetime import datetime

from hackernews import HackerNews

from newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("hackernews_adapter")


class HackerNewsAdapter(NewsletterAdapter):
    """Adapter for HackerNews using the haxor library."""

    def __init__(self, config):
        """Initialize with config.

        Note: We don't use the HTML-to-markdown functionality from base class.
        """
        super().__init__(config)
        self.hn = HackerNews()

    def scrape_date(self, date: str) -> dict:
        """Override template method for API-based fetching.

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            Normalized response dictionary
        """
        articles = []

        # Parse target date
        target_date = datetime.fromisoformat(util.format_date_for_url(date)).date()

        for story_type in self.config.types:
            util.log(
                f"[hackernews_adapter.scrape_date] Fetching {story_type} stories for {date}",
                logger=logger,
            )

            # Fetch stories from API
            try:
                # Top stories: fetch 5 (already ranked by HN)
                # Other types: fetch 100, then filter to top 5 by leading score
                fetch_limit = 5 if story_type == "top" else 100
                stories = self._fetch_stories_by_type(story_type, limit=fetch_limit)
            except Exception as e:
                util.log(
                    f"[hackernews_adapter.scrape_date] Error fetching {story_type}: {e}",
                    level=logging.ERROR,
                    exc_info=True,
                    logger=logger,
                )
                continue

            # Filter by date
            filtered_stories = [
                s for s in stories
                if s.submission_time.date() == target_date
            ]

            # For non-top types, sort by leading score and take top 5
            if story_type != "top" and filtered_stories:
                filtered_stories = self._get_leading_stories(filtered_stories, limit=5)

            util.log(
                f"[hackernews_adapter.scrape_date] Found {len(filtered_stories)}/{len(stories)} {story_type} stories for {date}",
                logger=logger,
            )

            # Convert to article format
            for story in filtered_stories:
                article = self._story_to_article(story, date, story_type)
                if article:
                    articles.append(article)

        # HackerNews doesn't have newsletter-style issues
        issues = []

        return self._normalize_response(articles, issues)

    def _get_leading_stories(self, stories: list, limit: int = 5) -> list:
        """Sort stories by leading score and return top N.

        Leading score = (2 * upvotes + comment_count)
        Upvotes are weighted twice as important as comments.

        Args:
            stories: List of HackerNews Item objects
            limit: Number of top stories to return

        Returns:
            List of top N stories sorted by leading score (descending)
        """
        def leading_score(story):
            score = story.score or 0
            comments = story.descendants or 0
            return (2 * score) + comments

        sorted_stories = sorted(stories, key=leading_score, reverse=True)
        return sorted_stories[:limit]

    def _fetch_stories_by_type(self, story_type: str, limit: int = 100):
        """Fetch stories from HackerNews API by type.

        Args:
            story_type: One of "top", "new", "ask", "show", "job"
            limit: Maximum number of stories to fetch

        Returns:
            List of Item objects
        """
        # Ensure we have an event loop in this thread
        # (Flask runs in threads without event loops)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if story_type == "top":
            return self.hn.top_stories(limit=limit)
        elif story_type == "new":
            return self.hn.new_stories(limit=limit)
        elif story_type == "ask":
            return self.hn.ask_stories(limit=limit)
        elif story_type == "show":
            return self.hn.show_stories(limit=limit)
        elif story_type == "job":
            return self.hn.job_stories(limit=limit)
        else:
            util.log(
                f"[hackernews_adapter._fetch_stories_by_type] Unknown story type: {story_type}",
                level=logging.WARNING,
                logger=logger,
            )
            return []

    def _story_to_article(self, story, date: str, story_type: str) -> dict | None:
        """Convert HackerNews Item to article dict.

        Args:
            story: HackerNews Item object
            date: Date string
            story_type: Story type (top, new, ask, show, job)

        Returns:
            Article dictionary or None if story should be skipped
        """
        # Skip stories without URLs (Ask HN, polls, etc. that are text-only)
        if not story.url:
            return None

        # Skip dead or deleted stories
        if story.dead or story.deleted:
            return None

        # Get category display name from config
        category = self.config.category_display_names.get(
            story_type, f"HN {story_type.capitalize()}"
        )

        return {
            "title": story.title or f"HN Story {story.item_id}",
            "url": story.url,
            "category": category,
            "date": util.format_date_for_url(date),
            "newsletter_type": story_type,
            "removed": False,
        }
```

### Success Criteria

#### Automated Verification
- [ ] Python syntax check: `uv run python3 -m py_compile hackernews_adapter.py`
- [ ] Import check: `uv run python3 -c "from hackernews_adapter import HackerNewsAdapter; print('Import successful')"`
- [ ] Adapter instantiation: `uv run python3 -c "from hackernews_adapter import HackerNewsAdapter; from newsletter_config import NEWSLETTER_CONFIGS; adapter = HackerNewsAdapter(NEWSLETTER_CONFIGS['hackernews']); print('Adapter created')"`

#### Manual Verification
- [ ] Test adapter with today's date (may return empty if no stories)
- [ ] Check response format matches standard (articles list, issues list, source_id)

**Implementation Note**: Since we don't have network access in this environment, manual testing will need to happen in an environment with internet access.

---

## Phase 4: Register HackerNews in Factory

### Overview
Update the factory function to return HackerNewsAdapter when appropriate.

### Changes Required

#### 1. Update Factory Function
**File**: `newsletter_scraper.py`

**Changes**: Update `_get_adapter_for_source()` around line 28

```python
# OLD:
def _get_adapter_for_source(config):
    if config.source_id.startswith("tldr_"):
        return TLDRAdapter(config)
    # elif config.source_id == "hackernews":
    #     return HackerNewsAdapter(config)
    else:
        raise ValueError(f"No adapter registered for source: {config.source_id}")

# NEW:
def _get_adapter_for_source(config):
    if config.source_id.startswith("tldr_"):
        return TLDRAdapter(config)
    elif config.source_id == "hackernews":
        from hackernews_adapter import HackerNewsAdapter
        return HackerNewsAdapter(config)
    else:
        raise ValueError(f"No adapter registered for source: {config.source_id}")
```

### Success Criteria

#### Automated Verification
- [ ] Python syntax check: `uv run python3 -m py_compile newsletter_scraper.py`
- [ ] Factory returns correct adapter: `uv run python3 -c "from newsletter_scraper import _get_adapter_for_source; from newsletter_config import NEWSLETTER_CONFIGS; from hackernews_adapter import HackerNewsAdapter; adapter = _get_adapter_for_source(NEWSLETTER_CONFIGS['hackernews']); assert isinstance(adapter, HackerNewsAdapter); print('Factory works')"`

#### Manual Verification
- [ ] Factory returns TLDRAdapter for TLDR sources
- [ ] Factory returns HackerNewsAdapter for HackerNews source
- [ ] Factory raises ValueError for unknown sources

---

## Phase 5: Integration Testing

### Overview
Test the full integration with real API calls and verify the response format.

### Manual Testing Steps

1. **Start the development server**:
   ```bash
   uv run python3 serve.py
   ```

2. **Test HackerNews source alone** (today's date):
   ```bash
   curl -X POST http://localhost:5001/api/scrape \
     -H "Content-Type: application/json" \
     -d "{\"start_date\": \"$(date +%Y-%m-%d)\", \"end_date\": \"$(date +%Y-%m-%d)\", \"sources\": [\"hackernews\"]}" \
     | jq .
   ```

3. **Verify response structure**:
   - `success: true`
   - `articles` array with items
   - Each article has: `source_id="hackernews"`, `category` (HN Top, HN New, etc.), `title`, `url`, `date`
   - `issues` array (empty for HackerNews)
   - `stats` object

4. **Test multi-source scraping** (HN + TLDR):
   ```bash
   curl -X POST http://localhost:5001/api/scrape \
     -H "Content-Type: application/json" \
     -d "{\"start_date\": \"$(date +%Y-%m-%d)\", \"end_date\": \"$(date +%Y-%m-%d)\", \"sources\": [\"tldr_ai\", \"hackernews\"]}" \
     | jq .
   ```

5. **Verify multi-source merging**:
   - Both `source_id="tldr_ai"` and `source_id="hackernews"` articles present
   - Articles sorted correctly
   - No URL collisions (same URL from different sources should not cause issues)

6. **Test date range** (if HackerNews had stories on these dates):
   ```bash
   curl -X POST http://localhost:5001/api/scrape \
     -H "Content-Type: application/json" \
     -d '{"start_date": "2025-10-25", "end_date": "2025-10-27", "sources": ["hackernews"]}' \
     | jq '.stats'
   ```

7. **Test in browser UI**:
   - Open http://localhost:5001
   - Select HackerNews source
   - Scrape today's date
   - Verify articles display correctly with "HN Top", "HN New" categories

### Success Criteria

#### Automated Verification
- [ ] Server starts without errors: `uv run python3 -c "import serve; print('Server module loads')"`
- [ ] All imports resolve: `uv run python3 -c "from newsletter_scraper import scrape_date_range; print('All imports work')"`

#### Manual Verification
- [ ] HackerNews stories appear in API response
- [ ] Multi-source scraping includes both TLDR and HackerNews
- [ ] No errors in server logs
- [ ] UI displays HackerNews articles correctly
- [ ] Articles from HackerNews have proper metadata (category, source_id, date)
- [ ] Date filtering works (only stories from requested date appear)

---

## Testing Strategy

### Unit Tests
Defer to future enhancement. Focus on integration testing first.

### Integration Tests
- Test factory returns correct adapter type
- Test HackerNewsAdapter returns valid response format
- Test multi-source scraping merges correctly
- Test date filtering works as expected

### Manual Testing Steps
As outlined in Phase 5 above.

## Migration Notes

Not applicable - this is a new source, not a migration.

## Potential Issues and Solutions

### Issue 1: HackerNews API Rate Limiting ✅ RESOLVED
**Problem**: Fetching 500 stories per type (4 types = 2000 stories) might trigger rate limits

**Solution Implemented**:
- **Top stories**: Fetch only 5 (already ranked by HN algorithm)
- **New/Ask/Show**: Fetch 100 each, then filter to top 5 by leading score
- **Leading score formula**: `(2 × upvotes) + comment_count` (upvotes weighted 2× comments)
- **Total API calls**: 5 + (3 × 100) = **305 max** (85% reduction from original plan)
- No retry logic needed - conservative limits avoid rate limiting entirely

### Issue 2: No Stories Found for Past Dates
**Problem**: HackerNews API only returns latest stories, may not have any from requested date

**Solution**:
- Accept this limitation (documented in "What We're NOT Doing")
- Log when no stories found for a date
- Return empty articles array (not an error)

### Issue 3: Stories Without URLs (Ask HN, Polls)
**Problem**: Some HackerNews items don't have URLs (text posts)

**Solution**:
- Skip these in `_story_to_article()` (return None)
- Log count of skipped stories

### Issue 4: Network Errors
**Problem**: HackerNews API might be unreachable or slow

**Solution**:
- Catch exceptions in `_fetch_stories_by_type()`
- Log errors but continue with other types
- Return partial results rather than failing completely

### Issue 5: Asyncio Event Loop in Flask Threads ✅ RESOLVED
**Problem**: haxor library uses asyncio internally, but Flask runs request handlers in threads without event loops

**Error Encountered**:
```
RuntimeError: There is no current event loop in thread 'Thread-1 (serve_forever)'
```

**Solution Implemented**:
- Added event loop creation in `_fetch_stories_by_type()`
- Check if loop exists and is open, create new one if needed
- Set as current event loop for the thread
- Code:
```python
try:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
```

**Testing Results**:
- ✅ HackerNews API calls work correctly
- ✅ No event loop errors
- ✅ TLDR sources unaffected (no regression)
- ✅ Multi-source scraping works (TLDR + HackerNews)

## References

- Research document: `agent-commands/output/hackernews-integration-research.md`
- haxor library: `https://github.com/avinassh/haxor`
- HackerNews API: `https://github.com/HackerNews/API`
- Current TLDR adapter: `tldr_adapter.py:45-421`
- Newsletter abstraction: `newsletter_adapter.py:19-154`
