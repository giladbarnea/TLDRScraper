"""
InfoQ adapter using RSS feed.

This adapter fetches articles from InfoQ via the RSS feed,
filtering by date and extracting article metadata.
InfoQ focuses on software architecture for senior engineers/architects.
"""

import logging
import re
from datetime import datetime
import requests
import feedparser

from newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("infoq_adapter")


class InfoQAdapter(NewsletterAdapter):
    """Adapter for InfoQ using RSS feed."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self.feed_url = "https://www.infoq.com/feed"

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch articles for a specific date from RSS feed.

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

        logger.info(
            f"[infoq_adapter.scrape_date] Fetching articles for {target_date_str} (excluding {len(excluded_urls)} URLs)"
        )

        try:
            response = requests.get(self.feed_url, timeout=10)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            logger.info(
                f"[infoq_adapter.scrape_date] Fetched {len(feed.entries)} total entries from feed"
            )

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

            logger.info(
                f"[infoq_adapter.scrape_date] Found {len(articles)} articles for {target_date_str}"
            )

        except Exception as e:
            logger.error(
                f"[infoq_adapter.scrape_date] Error fetching feed: {e}",
                exc_info=True
            )

        issues = []
        if articles:
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': self.config.category_display_names.get('articles', 'InfoQ'),
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from text.

        >>> adapter = InfoQAdapter(None)
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

        summary = entry.get('summary', entry.get('description', ''))
        summary_text = self._strip_html(summary) if summary else ''

        if summary_text:
            if len(summary_text) > 200:
                summary_text = summary_text[:200] + '...'

        article_meta = summary_text if summary_text else ""

        tags = [tag.get('term', '') for tag in entry.get('tags', [])]
        if tags:
            tags_str = ', '.join(tags[:3])
            if article_meta:
                article_meta = f"{article_meta} | Tags: {tags_str}"
            else:
                article_meta = f"Tags: {tags_str}"

        return {
            "title": title,
            "article_meta": article_meta,
            "url": link,
            "category": self.config.category_display_names.get('articles', 'InfoQ'),
            "date": date,
            "newsletter_type": "articles",
            "removed": False,
        }
