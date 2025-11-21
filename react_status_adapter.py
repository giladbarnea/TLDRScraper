"""React Status newsletter adapter implementation using RSS feed.

React Status is a weekly React newsletter from Cooper Press with 40k subscribers.
It covers React library updates, tutorials, tools, and community news.

The adapter:
1. Fetches the RSS feed which contains recent issues
2. For a given date, finds the matching issue
3. Parses article links from the HTML content in the RSS feed
4. Resolves tracking links to actual article URLs
"""

import logging
import re
from datetime import datetime
import feedparser
import requests
from bs4 import BeautifulSoup

from newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("react_status_adapter")

RSS_FEED_URL = "https://react.statuscode.com/rss"


class ReactStatusAdapter(NewsletterAdapter):
    """Adapter for React Status newsletter using RSS feed."""

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch React Status articles for a specific date using RSS feed.

        React Status publishes weekly on Wednesdays. This method:
        1. Fetches the RSS feed
        2. Finds the issue matching the target date
        3. Parses articles from the issue's HTML content
        4. Resolves tracking links to actual URLs

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

        logger.info(
            f"[react_status_adapter.scrape_date] Fetching RSS feed for {target_date_str} (excluding {len(excluded_urls)} URLs)"
        )

        try:
            feed = feedparser.parse(RSS_FEED_URL)

            if not feed.entries:
                logger.warning(
                    "[react_status_adapter.scrape_date] No entries found in RSS feed"
                )
                return self._normalize_response([], [])

            logger.info(
                f"[react_status_adapter.scrape_date] Fetched {len(feed.entries)} issues from RSS"
            )

            # Find the issue for the target date
            matching_entry = self._find_matching_issue(feed.entries, target_date)

            if not matching_entry:
                logger.info(
                    f"[react_status_adapter.scrape_date] No issue found for {target_date_str}"
                )
                return self._normalize_response([], [])

            # Parse articles from the issue
            parsed_articles = self._parse_issue_articles(
                matching_entry, target_date_str, excluded_set
            )

            articles.extend(parsed_articles)

            logger.info(
                f"[react_status_adapter.scrape_date] Found {len(articles)} articles for {target_date_str}"
            )

        except Exception as e:
            logger.error(
                f"[react_status_adapter.scrape_date] Error fetching RSS feed: {e}",
                exc_info=True
            )

        issues = []
        if articles:
            category = self.config.category_display_names.get("newsletter", "React Status")
            issue_title = matching_entry.get('title', '') if matching_entry else None
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': category,
                'title': issue_title,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _find_matching_issue(self, entries: list, target_date: datetime.date) -> dict | None:
        """Find the RSS entry matching the target date.

        React Status publishes weekly. This finds the issue published on or
        immediately before the target date.

        Args:
            entries: List of RSS feed entries
            target_date: Target date to match

        Returns:
            Matching RSS entry or None if not found
        """
        for entry in entries:
            published_parsed = entry.get('published_parsed')
            if not published_parsed:
                continue

            entry_date = datetime(*published_parsed[:3]).date()

            # For weekly newsletters, use the exact date or find the most recent issue
            if entry_date == target_date:
                return entry

        return None

    def _parse_issue_articles(
        self, entry: dict, date_str: str, excluded_set: set
    ) -> list[dict]:
        """Parse articles from an RSS feed entry.

        Args:
            entry: RSS feed entry dictionary
            date_str: Date string in YYYY-MM-DD format
            excluded_set: Set of canonical URLs to exclude

        Returns:
            List of article dictionaries
        """
        summary_html = entry.get('summary', '')
        if not summary_html:
            return []

        soup = BeautifulSoup(summary_html, 'html.parser')
        articles = []

        # Find article titles - they have bold/large font styling
        title_spans = soup.find_all('span', style=re.compile(r'font-weight:\s*600'))

        category = self.config.category_display_names.get("newsletter", "React Status")

        for span in title_spans:
            link = span.find('a', href=True)
            if not link:
                continue

            tracking_url = link.get('href', '')
            title = link.get_text(strip=True)
            domain = link.get('title', '')

            if not title or len(title) < 5:
                continue

            # Find metadata (author/description)
            parent_p = span.find_parent('p')
            article_meta = ""

            if parent_p:
                next_p = parent_p.find_next_sibling('p')
                if next_p:
                    meta_text = next_p.get_text(strip=True)
                    if 'sponsor' not in meta_text.lower():
                        article_meta = meta_text

            # Resolve tracking link to actual URL
            try:
                actual_url = self._resolve_tracking_link(tracking_url)
                if not actual_url:
                    continue

                canonical_url = util.canonicalize_url(actual_url)

                # Skip excluded URLs and sponsor articles
                if canonical_url in excluded_set:
                    continue
                if 'sponsor' in (article_meta.lower() or '') or 'sponsor' in title.lower():
                    continue

                articles.append({
                    "title": title,
                    "article_meta": article_meta,
                    "url": canonical_url,
                    "category": category,
                    "date": date_str,
                    "newsletter_type": "newsletter",
                    "removed": False,
                })

            except Exception as e:
                logger.warning(
                    f"[react_status_adapter._parse_issue_articles] Error processing article '{title}': {e}"
                )
                continue

        return articles

    def _resolve_tracking_link(self, tracking_url: str) -> str | None:
        """Resolve a tracking link to the actual destination URL.

        Args:
            tracking_url: Tracking URL from the newsletter

        Returns:
            Actual destination URL or None if resolution fails
        """
        try:
            response = requests.head(
                tracking_url,
                allow_redirects=True,
                timeout=10,
                headers={"User-Agent": self.config.user_agent}
            )
            return response.url
        except Exception as e:
            logger.warning(
                f"[react_status_adapter._resolve_tracking_link] Error resolving {tracking_url}: {e}"
            )
            return None
