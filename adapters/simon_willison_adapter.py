"""
Simon Willison's blog adapter using Atom RSS feed.

This adapter fetches articles from Simon Willison's blog via the Atom feed,
filtering by date and extracting article metadata.
"""

import logging
import re
from datetime import datetime

import feedparser

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("simon_willison_adapter")


class SimonWillisonAdapter(NewsletterAdapter):
    """Adapter for Simon Willison's blog using Atom RSS feed."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self.feed_url = "https://simonwillison.net/atom/everything/"

    @util.retry()
    def _fetch_feed(self):
        """Fetch RSS feed content."""
        response = util.fetch(self.feed_url, timeout=10)
        response.raise_for_status()
        return response.content

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch blog posts for a specific date from RSS feed.

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

        logger.info(f"Fetching articles for {target_date_str} (excluding {len(excluded_urls)} URLs)")

        try:
            feed_content = self._fetch_feed()
            feed = feedparser.parse(feed_content)

            logger.info(f"Fetched {len(feed.entries)} total entries from feed")

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

                link = self._clean_url(link)
                canonical_url = util.canonicalize_url(link)

                if canonical_url in excluded_set:
                    continue

                article = self._entry_to_article(entry, target_date_str)
                if article:
                    articles.append(article)

            logger.info(f"Found {len(articles)} articles for {target_date_str}")

        except Exception as e:
            logger.error(f"Error fetching feed: {e}", exc_info=True)

        issues = []
        if articles:
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': self.config.category_display_names.get('blog', 'Simon Willison'),
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _clean_url(self, url: str) -> str:
        """Remove feed-specific fragments from URL.

        >>> adapter = SimonWillisonAdapter(None)
        >>> adapter._clean_url("https://example.com/post/#atom-everything")
        'https://example.com/post/'
        """
        if '#atom-everything' in url:
            url = url.replace('#atom-everything', '')
        return url

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from text.

        >>> adapter = SimonWillisonAdapter(None)
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

        link = self._clean_url(entry.get('link', ''))
        if not link:
            return None

        summary = entry.get('summary', '')
        summary_text = self._strip_html(summary) if summary else ''

        if summary_text:
            if len(summary_text) > 200:
                summary_text = summary_text[:200] + '...'

        tags = [tag.term for tag in entry.get('tags', [])]
        if tags:
            tags_str = ', '.join(tags[:5])
            article_meta = f"Tags: {tags_str}"
        else:
            article_meta = ""

        return {
            "title": title,
            "article_meta": article_meta,
            "url": link,
            "category": self.config.category_display_names.get('blog', 'Simon Willison'),
            "date": date,
            "newsletter_type": "blog",
            "removed": False,
        }
