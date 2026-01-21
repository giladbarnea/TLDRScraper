"""
Armin Ronacher (lucumr.pocoo.org) blog adapter using Atom feed.
"""

import logging
from datetime import datetime

import feedparser

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("lucumr_adapter")


class LucumrAdapter(NewsletterAdapter):
    """Adapter for Armin Ronacher's blog using Atom feed."""

    def __init__(self, config):
        super().__init__(config)
        self.feed_url = "https://lucumr.pocoo.org/feed.atom"

    @util.retry()
    def _fetch_feed(self):
        """Fetch Atom feed content."""
        response = util.fetch(self.feed_url, timeout=10)
        response.raise_for_status()
        return response.content

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch blog posts for a specific date from Atom feed.

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
                'category': self.config.category_display_names.get('blog', "Armin Ronacher"),
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _entry_to_article(self, entry: dict, date: str) -> dict | None:
        """Convert Atom feed entry to article dict.

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
        if summary and len(summary) > 300:
            summary = summary[:300] + '...'

        return {
            "title": title,
            "article_meta": summary if summary else "",
            "url": link,
            "category": self.config.category_display_names.get('blog', "Armin Ronacher"),
            "date": date,
            "newsletter_type": "blog",
            "removed": False,
        }
