"""
Cloudflare Blog adapter using RSS feed.

Cloudflare Blog (blog.cloudflare.com) covers deep technical topics on networking,
security, edge computing, and performance optimization. High-quality technical content
from a leading CDN and security provider.
"""

import logging
import re
from datetime import datetime
import requests
import feedparser

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("cloudflare_adapter")

RSS_FEED_URL = "https://blog.cloudflare.com/rss/"


class CloudflareAdapter(NewsletterAdapter):
    """Adapter for Cloudflare Blog using RSS feed."""

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch Cloudflare blog posts for a specific date using RSS feed.

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

        logger.info(f"[cloudflare_adapter.scrape_date] Fetching RSS feed for {target_date_str}")

        try:
            response = requests.get(RSS_FEED_URL, timeout=10)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                logger.warning(f"[cloudflare_adapter.scrape_date] No entries found in RSS feed")
                return self._normalize_response([], [])

            logger.info(f"[cloudflare_adapter.scrape_date] Fetched {len(feed.entries)} entries from RSS")

            for entry in feed.entries:
                article = self._parse_rss_entry(entry, target_date, excluded_set)
                if article:
                    articles.append(article)

            logger.info(f"[cloudflare_adapter.scrape_date] Found {len(articles)} articles for {target_date_str}")

        except Exception as e:
            logger.error(f"[cloudflare_adapter.scrape_date] Error fetching RSS feed: {e}", exc_info=True)

        issues = []
        if articles:
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': 'Cloudflare Blog',
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
        description = entry.get('description', '')

        description_text = self._strip_html(description) if description else ''

        if description_text:
            if len(description_text) > 150:
                description_text = description_text[:150] + '...'
            article_meta = description_text
        else:
            article_meta = ""

        return {
            "title": title,
            "article_meta": article_meta,
            "url": entry['link'],
            "category": "Cloudflare Blog",
            "date": util.format_date_for_url(entry_date),
            "newsletter_type": "blog",
            "removed": False,
        }

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from text.

        >>> from newsletter_config import NEWSLETTER_CONFIGS
        >>> adapter = CloudflareAdapter(NEWSLETTER_CONFIGS['cloudflare'])
        >>> adapter._strip_html("<p>Hello <b>world</b></p>")
        'Hello world'
        """
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
