"""
Xe Iaso blog adapter implementation using RSS feed.

Xe Iaso (xeiaso.net) is a technical educator with 400+ blog articles covering
backend systems, NixOS, systems programming, and making tech accessible.
Posts 1-2 articles per week.
"""

import logging
from datetime import datetime
import feedparser

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("xeiaso_adapter")

RSS_FEED_URL = "https://xeiaso.net/blog.rss"


class XeIasoAdapter(NewsletterAdapter):
    """Adapter for Xe Iaso's blog using RSS feed."""

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch Xe Iaso blog posts for a specific date using RSS feed.

        Args:
            date: Date string in YYYY-MM-DD format
            excluded_urls: List of canonical URLs to exclude from results

        Returns:
            Normalized response dictionary with articles and issues
        """
        articles = []
        excluded_set = set(excluded_urls)

        target_date_str = util.format_date_for_url(date)
        target_date = datetime.fromisoformat(target_date_str).date()

        logger.info(f"Fetching RSS feed for {target_date_str}")

        try:
            feed = feedparser.parse(RSS_FEED_URL)

            if not feed.entries:
                logger.warning(f"No entries found in RSS feed")
                return self._normalize_response([], [])

            logger.info(f"Fetched {len(feed.entries)} entries from RSS")

            for entry in feed.entries:
                article = self._parse_rss_entry(entry, target_date, excluded_set)
                if article:
                    articles.append(article)

            logger.info(f"Found {len(articles)} articles for {target_date_str}")

        except Exception as e:
            logger.error(f"Error fetching RSS feed: {e}", exc_info=True)

        issues = []
        if articles:
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': 'Xe Iaso',
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _parse_rss_entry(self, entry: dict, target_date: datetime.date, excluded_set: set) -> dict | None:
        """Parse RSS entry into article dict if it matches the target date.

        Args:
            entry: feedparser entry dict
            target_date: Target date to filter by
            excluded_set: Set of canonical URLs to exclude

        Returns:
            Article dictionary or None if entry should be skipped
        """
        if not entry.get('link'):
            return None

        canonical_url = util.canonicalize_url(entry['link'])
        if canonical_url in excluded_set:
            return None

        published_parsed = entry.get('published_parsed')
        if not published_parsed:
            return None

        entry_date = datetime(*published_parsed[:3]).date()

        if entry_date != target_date:
            return None

        title = entry.get('title', 'Untitled')
        summary = entry.get('summary', '')

        tags = entry.get('tags', [])
        tag_terms = [tag.get('term', '') for tag in tags]

        is_external = 'external' in tag_terms

        if is_external:
            article_meta = "External post"
        else:
            article_meta = summary[:100] if summary else ""

        return {
            "title": title,
            "article_meta": article_meta,
            "url": entry['link'],
            "category": "Xe Iaso",
            "date": util.format_date_for_url(entry_date),
            "newsletter_type": "blog",
            "removed": False,
        }
