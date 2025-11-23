"""
Google DeepMind blog adapter using HTML scraping.

This adapter fetches articles from the Google DeepMind blog by scraping
the blog listing page, filtering by date and extracting article metadata.
"""

import logging
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("deepmind_adapter")


class DeepMindAdapter(NewsletterAdapter):
    """Adapter for Google DeepMind blog using HTML scraping."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self.blog_url = "https://deepmind.google/discover/blog/"

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch blog posts for a specific date from blog listing page.

        Args:
            date: Date string in YYYY-MM-DD format
            excluded_urls: List of canonical URLs to exclude from results

        Returns:
            Normalized response dictionary
        """
        articles = []
        excluded_set = set(excluded_urls)

        target_date = datetime.fromisoformat(util.format_date_for_url(date))
        target_month_year = target_date.strftime("%B %Y")

        logger.info(f"[deepmind_adapter.scrape_date] Fetching articles for {target_month_year} (excluding {len(excluded_urls)} URLs)")

        try:
            response = requests.get(self.blog_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            article_cards = soup.find_all('article', class_='card-blog')

            logger.info(f"[deepmind_adapter.scrape_date] Found {len(article_cards)} total articles on blog page")

            for card in article_cards:
                time_elem = card.find('time')
                if not time_elem:
                    continue

                article_date_str = time_elem.get('datetime', '').strip()

                if article_date_str != target_month_year:
                    continue

                link_elem = card.find('a', class_='button')
                if not link_elem:
                    continue

                href = link_elem.get('href', '')
                if not href.startswith('/'):
                    continue

                full_url = 'https://deepmind.google' + href
                canonical_url = util.canonicalize_url(full_url)

                if canonical_url in excluded_set:
                    continue

                article = self._card_to_article(card, target_date.strftime("%Y-%m-%d"))
                if article:
                    articles.append(article)

            logger.info(f"[deepmind_adapter.scrape_date] Found {len(articles)} articles for {target_month_year}")

        except Exception as e:
            logger.error(f"[deepmind_adapter.scrape_date] Error fetching blog: {e}", exc_info=True)

        issues = []
        if articles:
            issues.append({
                'date': target_date.strftime("%Y-%m-%d"),
                'source_id': self.config.source_id,
                'category': self.config.category_display_names.get('blog', 'Google DeepMind'),
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _card_to_article(self, card, date: str) -> dict | None:
        """Convert blog article card to article dict.

        Args:
            card: BeautifulSoup article card element
            date: Date string in YYYY-MM-DD format

        Returns:
            Article dictionary or None if card should be skipped
        """
        title_elem = card.find('h3', class_='card__title')
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)
        if not title:
            return None

        link_elem = card.find('a', class_='button')
        if not link_elem:
            return None

        href = link_elem.get('href', '')
        if not href.startswith('/'):
            return None

        full_url = 'https://deepmind.google' + href

        category_elem = card.find('span', class_='meta__category')
        category_tag = category_elem.get_text(strip=True) if category_elem else ''

        article_meta = f"Category: {category_tag}" if category_tag else ""

        return {
            "title": title,
            "article_meta": article_meta,
            "url": full_url,
            "category": self.config.category_display_names.get('blog', 'Google DeepMind'),
            "date": date,
            "newsletter_type": "blog",
            "removed": False,
        }
