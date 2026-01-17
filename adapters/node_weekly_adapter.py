"""Node Weekly adapter implementation.

This adapter implements the NewsletterAdapter interface for Node Weekly newsletter,
which publishes weekly issues about Node.js news and articles.

The adapter:
1. Fetches the RSS feed to build a date-to-issue mapping (cached)
2. For a given date, finds the closest previous issue
3. Scrapes article titles and URLs from the issue page
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime

from bs4 import BeautifulSoup

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("node_weekly_adapter")

# RSS feed URL
RSS_FEED_URL = "https://cprss.s3.amazonaws.com/nodeweekly.com.xml"


class NodeWeeklyAdapter(NewsletterAdapter):
    """Adapter for Node Weekly newsletter."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self._date_to_issue_cache = None

    @util.retry()
    def _fetch(self, url: str, *, timeout: int = 30):
        """Fetch URL and return response."""
        response = util.fetch(url, timeout=timeout)
        response.raise_for_status()
        return response

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch Node Weekly articles for a specific date.

        Strategy:
        1. Fetch RSS feed to get date-to-issue mapping (cached)
        2. Find issue for the requested date (or closest previous)
        3. Scrape articles from issue page

        Args:
            date: Date string in YYYY-MM-DD format
            excluded_urls: List of canonical URLs to exclude from results

        Returns:
            Normalized response dictionary
        """
        articles = []
        excluded_set = set(excluded_urls)

        date_str = util.format_date_for_url(date)

        logger.info(f"Scraping Node Weekly for {date_str} (excluding {len(excluded_urls)} URLs)")

        try:
            issue_data = self._get_issue_for_date(date_str)

            if not issue_data:
                logger.info(f"No issue found for {date_str}")
                return self._normalize_response([], [])

            issue_url = issue_data['url']
            issue_date = issue_data['date']
            issue_number = issue_data['issue_number']

            logger.info(f"Found issue #{issue_number} at {issue_url} (published {issue_date})")

            scraped_articles = self._scrape_issue(issue_url, issue_date, issue_number)

            for article in scraped_articles:
                canonical_url = util.canonicalize_url(article['url'])
                if canonical_url not in excluded_set:
                    articles.append(article)

            logger.info(f"Scraped {len(articles)} articles after filtering")

        except Exception as e:
            logger.error(f"Error scraping Node Weekly for {date_str}: {e}", exc_info=True)

        category = self.config.category_display_names.get("newsletter", "Node Weekly")
        issues = []
        if articles:
            issues = [{
                'date': date_str,
                'source_id': self.config.source_id,
                'category': category,
                'title': f"Issue #{issue_number}" if issue_number else None,
                'subtitle': None
            }]

        return self._normalize_response(articles, issues)

    def _get_issue_for_date(self, target_date: str) -> dict | None:
        """Get issue data for a specific date by finding closest previous issue.

        Args:
            target_date: Date string in YYYY-MM-DD format

        Returns:
            Dictionary with issue data or None if not found
        """
        if self._date_to_issue_cache is None:
            self._date_to_issue_cache = self._build_date_to_issue_mapping()

        target_dt = datetime.fromisoformat(target_date)

        # Find the closest previous issue
        closest_issue = None
        closest_date = None

        for issue_date_str, issue_data in self._date_to_issue_cache.items():
            issue_dt = datetime.fromisoformat(issue_date_str)

            # Only consider issues on or before target date
            if issue_dt <= target_dt:
                if closest_date is None or issue_dt > closest_date:
                    closest_date = issue_dt
                    closest_issue = issue_data

        return closest_issue

    def _build_date_to_issue_mapping(self) -> dict[str, dict]:
        """Build mapping of dates to issue data from RSS feed.

        Returns:
            Dictionary mapping YYYY-MM-DD strings to issue data dicts
        """
        logger.info(f"Fetching RSS feed from {RSS_FEED_URL}")

        response = self._fetch(RSS_FEED_URL, timeout=30)
        root = ET.fromstring(response.content)
        items = root.findall('.//item')

        date_to_issue = {}

        for item in items:
            try:
                link_elem = item.find('link')
                pub_date_elem = item.find('pubDate')

                if link_elem is None or pub_date_elem is None:
                    continue

                link = link_elem.text
                pub_date_str = pub_date_elem.text

                # Parse date: "Tue, 18 Nov 2025 00:00:00 +0000"
                pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
                formatted_date = pub_date.strftime('%Y-%m-%d')

                # Extract issue number from URL: https://nodeweekly.com/issues/601
                issue_match = re.search(r'/issues/(\d+)', link)
                issue_number = issue_match.group(1) if issue_match else None

                date_to_issue[formatted_date] = {
                    'url': link,
                    'date': formatted_date,
                    'issue_number': issue_number
                }

            except Exception as e:
                logger.warning(f"Error parsing RSS item: {e}")
                continue

        logger.info(f"Built mapping for {len(date_to_issue)} issues")

        return date_to_issue

    def _scrape_issue(self, issue_url: str, date_str: str, issue_number: str) -> list[dict]:
        """Scrape articles from a Node Weekly issue page.

        Args:
            issue_url: URL of the issue page
            date_str: Date string in YYYY-MM-DD format
            issue_number: Issue number

        Returns:
            List of article dictionaries
        """
        time.sleep(0.2)  # Rate limiting

        response = self._fetch(issue_url, timeout=30)
        markdown = self._html_to_markdown(response.text)

        # Parse articles from markdown
        articles = self._parse_articles_from_markdown(markdown, date_str, issue_number)

        return articles

    def _parse_articles_from_markdown(self, markdown: str, date_str: str, issue_number: str) -> list[dict]:
        """Parse articles from markdown content.

        Args:
            markdown: Markdown content
            date_str: Date string in YYYY-MM-DD format
            issue_number: Issue number

        Returns:
            List of article dictionaries
        """
        articles = []
        category = self.config.category_display_names.get("newsletter", "Node Weekly")

        # Extract all markdown links: [title](url)
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        matches = link_pattern.findall(markdown)

        for title, url in matches:
            # Clean URL - remove any trailing quoted text from markdown title syntax
            url = url.split()[0] if ' ' in url else url

            # Skip if not a tracking link
            if 'nodeweekly.com/link/' not in url:
                continue

            # Skip meta links
            if any(skip in title.lower() for skip in [
                'read on the web',
                'unsubscribe',
                'archive',
                'view in browser',
                'sponsor',
                'node weekly',
                'node.js weekly',
                'prev',
                'next',
                '« prev',
                'next »'
            ]):
                continue

            # Skip very short titles (likely inline links)
            if len(title) < 10:
                continue

            # Clean up title - remove quotes and trailing URLs that might be in markdown link definitions
            cleaned_title = title.strip()

            # Remove trailing quoted URLs like ' "example.com"' from markdown links
            cleaned_title = re.sub(r'\s+"[^"]+"\s*$', '', cleaned_title)

            # Skip if title is just punctuation or numbers
            if re.match(r'^[\d\s\-\.\,]+$', cleaned_title):
                continue

            articles.append({
                "title": cleaned_title,
                "article_meta": "",
                "url": url,
                "category": category,
                "date": date_str,
                "newsletter_type": "newsletter",
                "removed": False,
            })

        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for article in articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)

        return unique_articles
