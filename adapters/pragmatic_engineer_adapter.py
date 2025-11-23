"""
The Pragmatic Engineer newsletter adapter using RSS feed.

This adapter fetches articles from The Pragmatic Engineer newsletter (by Gergely Orosz)
via the Substack RSS feed. The newsletter covers senior engineering topics, industry insights,
scaling teams, tech trends, and the popular "The Scoop" series.
"""

import logging
import re
from datetime import datetime
import requests
import feedparser

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("pragmatic_engineer_adapter")

RSS_FEED_URL = "https://newsletter.pragmaticengineer.com/feed"


class PragmaticEngineerAdapter(NewsletterAdapter):
    """Adapter for The Pragmatic Engineer newsletter using Substack RSS feed."""

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch newsletter articles for a specific date using RSS feed.

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

        logger.info(f"[pragmatic_engineer_adapter.scrape_date] Fetching RSS feed for {target_date_str}")

        try:
            headers = {
                'User-Agent': self.config.user_agent
            }
            response = requests.get(RSS_FEED_URL, headers=headers, timeout=10)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                logger.warning(f"[pragmatic_engineer_adapter.scrape_date] No entries found in RSS feed")
                return self._normalize_response([], [])

            logger.info(f"[pragmatic_engineer_adapter.scrape_date] Fetched {len(feed.entries)} total entries from RSS")

            for entry in feed.entries:
                article = self._parse_rss_entry(entry, target_date, excluded_set)
                if article:
                    articles.append(article)

            logger.info(f"[pragmatic_engineer_adapter.scrape_date] Found {len(articles)} articles for {target_date_str}")

        except Exception as e:
            logger.error(f"[pragmatic_engineer_adapter.scrape_date] Error fetching RSS feed: {e}", exc_info=True)

        issues = []
        if articles:
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': 'The Pragmatic Engineer',
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

        article_meta = self._extract_article_meta(summary)

        return {
            "title": title,
            "article_meta": article_meta,
            "url": entry['link'],
            "category": "The Pragmatic Engineer",
            "date": util.format_date_for_url(entry_date),
            "newsletter_type": "newsletter",
            "removed": False,
        }

    def _extract_article_meta(self, summary: str) -> str:
        """Extract clean article metadata from HTML summary.

        Args:
            summary: HTML summary from RSS feed

        Returns:
            Clean text excerpt for article_meta
        """
        clean_text = re.sub(r'<[^>]+>', '', summary)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        if len(clean_text) > 200:
            clean_text = clean_text[:200] + '...'

        return clean_text
