---
last_updated: 2025-12-25 09:46
---
# Mathy AI (AI With Mike) Adapter Implementation Plan

## Overview

Add a new newsletter adapter for "Mathy AI" Substack (aiwithmike.substack.com) to scrape daily AI/ML paper reviews and blog posts. This follows the established Substack RSS adapter pattern used by LennyNewsletterAdapter, ByteByteGoAdapter, and PragmaticEngineerAdapter.

## Current State Analysis

The codebase has 22 newsletter adapters with a well-established pattern for Substack-based sources:
- Factory pattern at `newsletter_scraper.py:15-93` maps source_id to adapter classes
- Declarative config at `newsletter_config.py:31-289` defines source metadata
- RSS-based adapters override `scrape_date()` to use feedparser instead of HTML parsing

### Key Discoveries:
- RSS feed confirmed working at `https://aiwithmike.substack.com/feed`
- Author in feed: "Mike Erlihson, Mathy AI"
- Feed uses standard Substack RSS format with `published_parsed`, `title`, `link`, `summary`
- Existing Substack adapters at `adapters/lenny_newsletter_adapter.py:21-143`, `adapters/bytebytego_adapter.py:21-141` provide exact template
- Current highest sort_order is 20 (node_weekly) at `newsletter_config.py:287`

## Desired End State

A fully functional `AiWithMikeAdapter` that:
1. Fetches articles from `https://aiwithmike.substack.com/feed`
2. Filters by requested date
3. Returns normalized article/issue data matching existing schema
4. Is registered in the factory and config

**Verification**: `curl http://localhost:5001/api/scrape?sources=aiwithmike` returns articles for dates with published content.

## What We're NOT Doing

- No database schema changes (uses existing article/issue tables)
- No client UI changes (existing UI handles new sources automatically)
- No new dependencies (feedparser already installed)
- No tests (no existing adapter-specific tests in codebase)

## Implementation Approach

Single-phase implementation following the exact pattern of `ByteByteGoAdapter` with minimal modifications for source-specific details.

## Phase 1: Add Mathy AI Adapter

### Overview
Create the adapter class, register it in config, and wire up the factory.

### Changes Required:

#### 1. Newsletter Configuration
**File**: `newsletter_config.py`
**Changes**: Add new entry to `NEWSLETTER_CONFIGS` dict after line 288 (before closing brace)

```python
    "aiwithmike": NewsletterSourceConfig(
        source_id="aiwithmike",
        display_name="Mathy AI",
        base_url="https://aiwithmike.substack.com",
        url_pattern="",
        types=["newsletter"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"newsletter": "Mathy AI"},
        sort_order=21,
    ),
```

#### 2. Adapter Implementation
**File**: `adapters/aiwithmike_adapter.py` (new file)
**Changes**: Create new adapter following ByteByteGoAdapter pattern

```python
"""
Mathy AI newsletter adapter using Substack RSS feed.

This adapter fetches articles from Mathy AI's Substack via the RSS feed,
filtering by date and extracting article metadata.
"""

import logging
import re
from datetime import datetime
import requests
import feedparser

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("aiwithmike_adapter")


class AiWithMikeAdapter(NewsletterAdapter):
    """Adapter for Mathy AI newsletter using Substack RSS feed."""

    def __init__(self, config):
        super().__init__(config)
        self.feed_url = "https://aiwithmike.substack.com/feed"

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch newsletter articles for a specific date from RSS feed.

        Args:
            date: Date string in YYYY-MM-DD format
            excluded_urls: List of canonical URLs to exclude from results

        Returns:
            Normalized response dictionary
        """
        articles = []
        excluded_set = set(excluded_urls)

        target_date = datetime.fromisoformat(util.format_date_for_url(date))
        target_date_str = target_date.strftime("%Y-%m-%d")

        logger.info(f"[aiwithmike_adapter.scrape_date] Fetching articles for {target_date_str} (excluding {len(excluded_urls)} URLs)")

        try:
            response = requests.get(self.feed_url, timeout=10)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            logger.info(f"[aiwithmike_adapter.scrape_date] Fetched {len(feed.entries)} total entries from feed")

            for entry in feed.entries:
                if not entry.get('published_parsed'):
                    continue

                entry_date = datetime(*entry.published_parsed[:6])
                entry_date_str = entry_date.strftime("%Y-%m-%d")

                if entry_date_str != target_date_str:
                    continue

                link = entry.get('link', '')
                if not link:
                    continue

                canonical_url = util.canonicalize_url(link)

                if canonical_url in excluded_set:
                    continue

                article = self._entry_to_article(entry, target_date_str)
                if article:
                    articles.append(article)

            logger.info(f"[aiwithmike_adapter.scrape_date] Found {len(articles)} articles for {target_date_str}")

        except Exception as e:
            logger.error(f"[aiwithmike_adapter.scrape_date] Error fetching feed: {e}", exc_info=True)

        issues = []
        if articles:
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': self.config.category_display_names.get('newsletter', 'Mathy AI'),
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from text.

        >>> adapter = AiWithMikeAdapter(None)
        >>> adapter._strip_html("<p>Hello <b>world</b></p>")
        'Hello world'
        """
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _entry_to_article(self, entry: dict, date: str) -> dict | None:
        """Convert RSS feed entry to article dict.

        Args:
            entry: feedparser entry dictionary
            date: Date string

        Returns:
            Article dictionary or None if entry should be skipped
        """
        title = entry.get('title', '')
        if not title:
            return None

        link = entry.get('link', '')
        if not link:
            return None

        summary = entry.get('summary', '')
        summary_text = self._strip_html(summary) if summary else ''

        if summary_text:
            if len(summary_text) > 200:
                summary_text = summary_text[:200] + '...'

        article_meta = summary_text if summary_text else ""

        return {
            "title": title,
            "article_meta": article_meta,
            "url": link,
            "category": self.config.category_display_names.get('newsletter', 'Mathy AI'),
            "date": date,
            "newsletter_type": "newsletter",
            "removed": False,
        }
```

#### 3. Factory Registration
**File**: `newsletter_scraper.py`
**Changes**: Add elif branch after line 91 (before the else clause at line 92)

```python
    elif config.source_id == "aiwithmike":
        from adapters.aiwithmike_adapter import AiWithMikeAdapter
        return AiWithMikeAdapter(config)
```

### Success Criteria:

#### Automated Verification:
- [x] `uv run python3 -c "from adapters.aiwithmike_adapter import AiWithMikeAdapter; print('Import OK')"` succeeds
- [x] `uv run python3 -c "from newsletter_config import NEWSLETTER_CONFIGS; assert 'aiwithmike' in NEWSLETTER_CONFIGS; print('Config OK')"` succeeds
- [x] `uv run python3 -m doctest adapters/aiwithmike_adapter.py -v` passes the `_strip_html` doctest

#### Manual Verification:
- [x] Start server with `source setup.sh && start_server_and_watchdog`
- [x] `curl "http://localhost:5001/api/scrape?sources=aiwithmike&start_date=2025-12-22&end_date=2025-12-22"` returns article "When Models Judge Themselves"
- [x] Articles appear in the UI under "Mathy AI" category when browsing that date

## Testing Strategy

### Unit Tests:
- Doctest in `_strip_html` method validates HTML stripping

### Integration Tests:
- None required (no existing adapter-specific integration tests)

### Manual Testing Steps:
1. Start local server
2. Scrape a known date with content (2025-12-22 has "When Models Judge Themselves")
3. Verify article appears in API response with correct fields
4. Browse date in UI to confirm rendering

## References

- Similar implementation: `adapters/bytebytego_adapter.py:21-141`
- Factory pattern: `newsletter_scraper.py:15-93`
- Config schema: `newsletter_config.py:12-28`
- RSS feed: https://aiwithmike.substack.com/feed
