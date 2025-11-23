"""
Will Larson's "Irrational Exuberance" blog adapter implementation using RSS feed.

This adapter implements the NewsletterAdapter interface for Will Larson's blog,
using the RSS feed at lethain.com for efficient article fetching.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("will_larson_adapter")


class WillLarsonAdapter(NewsletterAdapter):
    """Adapter for Will Larson's blog using RSS feed."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self.rss_url = "https://lethain.com/feeds.xml"

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch articles from Will Larson's blog RSS feed for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format
            excluded_urls: List of canonical URLs to exclude from results

        Returns:
            Normalized response dictionary
        """
        articles = []
        excluded_set = set(excluded_urls)

        # Parse target date
        target_date = datetime.fromisoformat(util.format_date_for_url(date))
        target_date_str = target_date.strftime("%Y-%m-%d")

        logger.info(f"[will_larson_adapter.scrape_date] Fetching articles for {target_date_str} from RSS feed")

        try:
            # Fetch RSS feed
            response = requests.get(self.rss_url, timeout=10)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)
            items = root.findall('.//item')

            logger.info(f"[will_larson_adapter.scrape_date] Found {len(items)} items in RSS feed")

            # Filter items by date
            for item in items:
                title_elem = item.find('title')
                link_elem = item.find('link')
                pubdate_elem = item.find('pubDate')
                description_elem = item.find('description')

                if title_elem is None or link_elem is None or pubdate_elem is None:
                    continue

                # Parse publication date
                try:
                    pub_datetime = parsedate_to_datetime(pubdate_elem.text)
                    article_date_str = pub_datetime.strftime("%Y-%m-%d")
                except Exception as e:
                    logger.warning(f"[will_larson_adapter.scrape_date] Error parsing date '{pubdate_elem.text}': {e}")
                    continue

                # Check if article matches target date
                if article_date_str != target_date_str:
                    continue

                # Get article details
                title = title_elem.text
                url = link_elem.text
                canonical_url = util.canonicalize_url(url)

                # Skip if excluded
                if canonical_url in excluded_set:
                    continue

                # Extract excerpt from description (first 200 chars)
                description = description_elem.text if description_elem is not None else ""
                if description:
                    # Strip HTML tags and decode HTML entities
                    import re
                    import html
                    description_text = re.sub(r'<[^>]+>', '', description)
                    description_text = html.unescape(description_text)
                    excerpt = description_text[:200].strip()
                    if len(description_text) > 200:
                        excerpt += "..."
                else:
                    excerpt = ""

                article = {
                    "title": title,
                    "article_meta": excerpt,
                    "url": canonical_url,
                    "category": "Engineering Leadership",
                    "date": target_date_str,
                    "newsletter_type": "blog",
                    "removed": False,
                }

                articles.append(article)

            logger.info(f"[will_larson_adapter.scrape_date] Found {len(articles)} articles for {target_date_str}")

        except Exception as e:
            logger.error(f"[will_larson_adapter.scrape_date] Error fetching RSS feed: {e}", exc_info=True)

        # Create issue metadata if we have articles
        issues = []
        if articles:
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': 'Engineering Leadership',
                'title': 'Irrational Exuberance',
                'subtitle': 'Will Larson'
            })

        return self._normalize_response(articles, issues)
