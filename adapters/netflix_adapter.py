"""
Netflix Tech Blog adapter implementation using RSS feed.

This adapter implements the NewsletterAdapter interface for Netflix Tech Blog,
fetching articles from the Medium RSS feed and filtering them by publication date.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("netflix_adapter")


class NetflixAdapter(NewsletterAdapter):
    """Adapter for Netflix Tech Blog using Medium RSS feed."""

    def __init__(self, config):
        """Initialize with config.

        Note: We don't use the HTML-to-markdown functionality from base class.
        """
        super().__init__(config)
        self.rss_url = "https://medium.com/feed/netflix-techblog"

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch Netflix Tech Blog articles from RSS feed for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format
            excluded_urls: List of canonical URLs to exclude from results

        Returns:
            Normalized response dictionary
        """
        articles = []
        excluded_set = set(excluded_urls)

        target_date = datetime.fromisoformat(util.format_date_for_url(date))

        logger.info(f"[netflix_adapter.scrape_date] Fetching articles for {date} from RSS feed (excluding {len(excluded_urls)} URLs)")

        try:
            feed_items = self._fetch_rss_feed()

            logger.info(f"[netflix_adapter.scrape_date] Fetched {len(feed_items)} total items from RSS feed")

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

            logger.info(f"[netflix_adapter.scrape_date] {len(filtered_items)} articles match date {date}")

            # Convert to article format
            for item in filtered_items:
                article = self._rss_item_to_article(item, date)
                if article:
                    articles.append(article)

            logger.info(f"[netflix_adapter.scrape_date] Converted {len(articles)} items to articles")

        except Exception as e:
            logger.error(f"[netflix_adapter.scrape_date] Error fetching RSS feed: {e}", exc_info=True)

        # Create issue metadata if we have articles
        issues = []
        if articles:
            issues.append({
                'date': util.format_date_for_url(date),
                'source_id': self.config.source_id,
                'category': 'Netflix Tech',
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _fetch_rss_feed(self) -> list[dict]:
        """Fetch and parse the RSS feed.

        Returns:
            List of item dictionaries with title, link, pubDate, categories, description
        """
        response = requests.get(self.rss_url, timeout=30, headers={
            'User-Agent': self.config.user_agent
        })
        response.raise_for_status()

        root = ET.fromstring(response.content)
        channel = root.find('channel')

        if channel is None:
            logger.warning("[netflix_adapter._fetch_rss_feed] No channel found in RSS feed")
            return []

        items = []
        for item_elem in channel.findall('item'):
            title = item_elem.find('title')
            link = item_elem.find('link')
            pub_date = item_elem.find('pubDate')

            # Medium RSS feeds include content:encoded with full HTML
            content_ns = '{http://purl.org/rss/1.0/modules/content/}'
            content_encoded = item_elem.find(f'{content_ns}encoded')

            # Get all categories
            categories = [cat.text for cat in item_elem.findall('category') if cat.text]

            items.append({
                'title': title.text if title is not None else '',
                'link': link.text if link is not None else '',
                'pubDate': pub_date.text if pub_date is not None else '',
                'content': content_encoded.text if content_encoded is not None else '',
                'categories': categories,
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
            # RSS 2.0 uses RFC 822/2822 format: "Tue, 04 Nov 2025 20:33:44 GMT"
            return datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %Z')
        except ValueError:
            logger.warning(f"[netflix_adapter._parse_pub_date] Failed to parse date: {pub_date_str}")
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

        # Get categories for metadata
        categories = item.get('categories', [])
        category_str = ', '.join(categories[:3]) if categories else ''

        # Extract excerpt from content (strip HTML tags)
        content = item.get('content', '')
        excerpt = self._extract_text_from_html(content)[:150]

        # Build article_meta with categories and excerpt length
        article_meta_parts = []
        if category_str:
            article_meta_parts.append(category_str)
        if excerpt:
            article_meta_parts.append(f"{len(excerpt)} char excerpt")
        article_meta = ' | '.join(article_meta_parts) if article_meta_parts else ''

        return {
            "title": title,
            "article_meta": article_meta,
            "url": url,
            "category": "Netflix Tech",
            "date": util.format_date_for_url(date),
            "newsletter_type": "blog",
            "removed": False,
        }

    @staticmethod
    def _extract_text_from_html(html: str) -> str:
        """Extract plain text from HTML content.

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
        # Decode common HTML entities
        text = text.replace('&quot;', '"')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&#39;', "'")
        text = text.replace('&nbsp;', ' ')

        return text.strip()
