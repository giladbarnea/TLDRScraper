"""
Dan Luu blog adapter implementation using RSS feed.

This adapter implements the NewsletterAdapter interface for Dan Luu's blog,
fetching articles from the RSS feed and filtering them by publication date.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("danluu_adapter")


class DanLuuAdapter(NewsletterAdapter):
    """Adapter for Dan Luu's blog using RSS feed."""

    def __init__(self, config):
        """Initialize with config.

        Note: We don't use the HTML-to-markdown functionality from base class.
        """
        super().__init__(config)
        self.rss_url = "https://danluu.com/atom.xml"

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch Dan Luu blog articles from RSS feed for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format
            excluded_urls: List of canonical URLs to exclude from results

        Returns:
            Normalized response dictionary
        """
        articles = []
        excluded_set = set(excluded_urls)

        target_date = datetime.fromisoformat(util.format_date_for_url(date))

        util.log(
            f"[danluu_adapter.scrape_date] Fetching articles for {date} from RSS feed (excluding {len(excluded_urls)} URLs)",
            logger=logger,
        )

        try:
            feed_items = self._fetch_rss_feed()

            util.log(
                f"[danluu_adapter.scrape_date] Fetched {len(feed_items)} total items from RSS feed",
                logger=logger,
            )

            # Filter items by date and excluded URLs
            filtered_items = []
            for item in feed_items:
                pub_date = self._parse_pub_date(item.get('pubDate', ''))
                if pub_date is None:
                    continue

                # Check if article was published on target date
                if pub_date.date() != target_date.date():
                    continue

                # Check if URL is excluded
                url = item.get('link', '')
                if not url:
                    continue

                canonical_url = util.canonicalize_url(url)
                if canonical_url not in excluded_set:
                    filtered_items.append(item)

            util.log(
                f"[danluu_adapter.scrape_date] {len(filtered_items)} articles match date {date}",
                logger=logger,
            )

            # Convert to article format
            for item in filtered_items:
                article = self._rss_item_to_article(item, date)
                if article:
                    articles.append(article)

            util.log(
                f"[danluu_adapter.scrape_date] Converted {len(articles)} items to articles",
                logger=logger,
            )

        except Exception as e:
            util.log(
                f"[danluu_adapter.scrape_date] Error fetching RSS feed: {e}",
                level=logging.ERROR,
                exc_info=True,
                logger=logger,
            )

        # Create issue metadata if we have articles
        issues = []
        if articles:
            issues.append({
                'date': util.format_date_for_url(date),
                'source_id': self.config.source_id,
                'category': 'Dan Luu',
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _fetch_rss_feed(self) -> list[dict]:
        """Fetch and parse the RSS feed.

        Returns:
            List of item dictionaries with title, link, pubDate, description
        """
        response = requests.get(self.rss_url, timeout=30, headers={
            'User-Agent': self.config.user_agent
        })
        response.raise_for_status()

        root = ET.fromstring(response.content)
        channel = root.find('channel')

        if channel is None:
            util.log(
                "[danluu_adapter._fetch_rss_feed] No channel found in RSS feed",
                level=logging.WARNING,
                logger=logger,
            )
            return []

        items = []
        for item_elem in channel.findall('item'):
            title = item_elem.find('title')
            link = item_elem.find('link')
            pub_date = item_elem.find('pubDate')
            description = item_elem.find('description')

            items.append({
                'title': title.text if title is not None else '',
                'link': link.text if link is not None else '',
                'pubDate': pub_date.text if pub_date is not None else '',
                'description': description.text if description is not None else '',
            })

        return items

    def _parse_pub_date(self, pub_date_str: str) -> datetime | None:
        """Parse RSS pubDate format to datetime.

        Args:
            pub_date_str: Date string in RSS format (RFC 822/2822)

        Returns:
            datetime object or None if parsing fails
        """
        if not pub_date_str:
            return None

        try:
            # RSS 2.0 uses RFC 822/2822 format: "Mon, 28 Oct 2024 00:00:00 +0000"
            return datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
        except ValueError:
            util.log(
                f"[danluu_adapter._parse_pub_date] Failed to parse date: {pub_date_str}",
                level=logging.WARNING,
                logger=logger,
            )
            return None

    def _rss_item_to_article(self, item: dict, date: str) -> dict | None:
        """Convert RSS item to article dict.

        Args:
            item: RSS item dictionary
            date: Date string

        Returns:
            Article dictionary or None if item should be skipped
        """
        title = item.get('title', '').strip()
        url = item.get('link', '').strip()

        if not title or not url:
            return None

        # Extract excerpt from description (strip HTML tags)
        description = item.get('description', '')
        excerpt = self._extract_text_from_html(description)[:200]

        return {
            "title": title,
            "article_meta": f"{len(excerpt)} char excerpt",
            "url": url,
            "category": "Dan Luu",
            "date": util.format_date_for_url(date),
            "newsletter_type": "blog",
            "removed": False,
        }

    @staticmethod
    def _extract_text_from_html(html: str) -> str:
        """Extract plain text from HTML description.

        Args:
            html: HTML content

        Returns:
            Plain text with tags stripped
        """
        if not html:
            return ""

        # Simple tag removal (good enough for excerpts)
        import re
        text = re.sub(r'<[^>]+>', '', html)
        # Decode HTML entities
        text = text.replace('&quot;', '"')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&#39;', "'")

        return text.strip()
