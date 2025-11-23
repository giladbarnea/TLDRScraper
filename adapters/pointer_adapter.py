"""Pointer newsletter adapter implementation.

This adapter implements the NewsletterAdapter interface for Pointer.io newsletter,
which provides curated reading for engineering leaders.

The adapter:
1. Fetches the archives page to build a date-to-URL mapping
2. For a given date, finds the matching issue URL
3. Scrapes article titles and URLs from the issue page
"""

import logging
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("pointer_adapter")


class PointerAdapter(NewsletterAdapter):
    """Adapter for Pointer newsletter."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self._date_to_url_cache = None

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch Pointer articles for a specific date.

        Strategy:
        1. Fetch archives page to get date-to-URL mapping (cached)
        2. Find issue URL for the requested date
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

        logger.info(f"[pointer_adapter.scrape_date] Scraping Pointer for {date_str} (excluding {len(excluded_urls)} URLs)")

        try:
            issue_url = self._get_issue_url_for_date(date_str)

            if not issue_url:
                logger.info(f"[pointer_adapter.scrape_date] No issue found for {date_str}")
                return self._normalize_response([], [])

            logger.info(f"[pointer_adapter.scrape_date] Found issue URL: {issue_url}")

            scraped_articles = self._scrape_issue(issue_url, date_str)

            for article in scraped_articles:
                canonical_url = util.canonicalize_url(article['url'])
                if canonical_url not in excluded_set:
                    articles.append(article)

            logger.info(f"[pointer_adapter.scrape_date] Scraped {len(articles)} articles after filtering")

        except Exception as e:
            logger.error(f"[pointer_adapter.scrape_date] Error scraping Pointer for {date_str}: {e}", exc_info=True)

        category = self.config.category_display_names.get("newsletter", "Pointer")
        issues = []
        if articles:
            issues = [{
                'date': date_str,
                'source_id': self.config.source_id,
                'category': category,
                'title': None,
                'subtitle': None
            }]

        return self._normalize_response(articles, issues)

    def _get_issue_url_for_date(self, target_date: str) -> str | None:
        """Get issue URL for a specific date by parsing archives page.

        Args:
            target_date: Date string in YYYY-MM-DD format

        Returns:
            Issue URL or None if not found
        """
        if self._date_to_url_cache is None:
            self._date_to_url_cache = self._build_date_to_url_mapping()

        return self._date_to_url_cache.get(target_date)

    def _build_date_to_url_mapping(self) -> dict[str, str]:
        """Build mapping of dates to issue URLs from archives page.

        Returns:
            Dictionary mapping YYYY-MM-DD strings to issue URLs
        """
        archives_url = f"{self.config.base_url}/archives"

        logger.info(f"[pointer_adapter._build_date_to_url_mapping] Fetching archives from {archives_url}")

        response = requests.get(
            archives_url,
            timeout=30,
            headers={"User-Agent": self.config.user_agent}
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        issue_links = [link for link in links if '/archives/post_' in link['href']]

        date_to_url = {}
        for link in issue_links:
            href = link['href']
            text = link.get_text(strip=True)

            match = re.match(r'Issue #(\d+)(.+)', text)
            if match:
                date_str = match.group(2).strip()
                try:
                    date_obj = datetime.strptime(date_str, '%B %d, %Y')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    full_url = f"{self.config.base_url}{href}" if not href.startswith('http') else href
                    date_to_url[formatted_date] = full_url
                except Exception:
                    continue

        logger.info(f"[pointer_adapter._build_date_to_url_mapping] Built mapping for {len(date_to_url)} issues")

        return date_to_url

    def _scrape_issue(self, issue_url: str, date_str: str) -> list[dict]:
        """Scrape articles from a Pointer issue page.

        Args:
            issue_url: URL of the issue page
            date_str: Date string in YYYY-MM-DD format

        Returns:
            List of article dictionaries
        """
        response = requests.get(
            issue_url,
            timeout=30,
            headers={"User-Agent": self.config.user_agent}
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        h1_tags = soup.find_all('h1')

        articles = []
        category = self.config.category_display_names.get("newsletter", "Pointer")

        for h1 in h1_tags:
            link = h1.find('a', href=True)
            if not link or not link['href'].startswith('http'):
                continue

            url = link['href']

            if self._should_skip_url(url):
                continue

            title = link.get_text(strip=True)
            if not title:
                continue

            article_meta = self._extract_author(h1)

            articles.append({
                "title": title,
                "article_meta": article_meta,
                "url": url,
                "category": category,
                "date": date_str,
                "newsletter_type": "newsletter",
                "removed": False,
            })

        return articles

    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped (ads, internal links).

        Args:
            url: URL to check

        Returns:
            True if URL should be skipped
        """
        skip_domains = [
            'pointer.io',
            'beehiiv.com',
            'getunblocked.com',
            'forms.gle',
            'goo.gl',
        ]

        return any(domain in url for domain in skip_domains)

    def _extract_author(self, h1_tag) -> str:
        """Extract author from the element following the h1 tag.

        Args:
            h1_tag: BeautifulSoup h1 tag

        Returns:
            Author string or empty string
        """
        next_p = h1_tag.find_next('p')
        if next_p:
            author_text = next_p.get_text(strip=True)
            if author_text.startswith('—'):
                return author_text
        return ""
