"""
Google DeepMind blog adapter using HTML scraping.

This adapter fetches articles from the Google DeepMind blog by scraping
the blog listing page, filtering by date and extracting article metadata.

Note: The listing page shows "recently featured" dates, not original publication
dates. This adapter fetches each article page to get the real publication date.
"""

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("deepmind_adapter")


def _parse_date_string(date_str: str) -> str | None:
    """Parse date string to 'YYYY-MM-DD' format. Handles multiple formats.

    >>> _parse_date_string('December 19, 2025')
    '2025-12-19'
    >>> _parse_date_string('December 2025')
    '2025-12-01'
    >>> _parse_date_string('July 2024')
    '2024-07-01'
    >>> _parse_date_string('Invalid')
    """
    formats = [
        "%B %d, %Y",  # "December 19, 2025"
        "%B %Y",       # "December 2025" (fallback to first of month)
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


class DeepMindAdapter(NewsletterAdapter):
    """Adapter for Google DeepMind blog using HTML scraping."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self.blog_url = "https://deepmind.google/discover/blog/"

    @util.retry()
    def _fetch_page(self):
        """Fetch blog listing page."""
        response = util.fetch(self.blog_url, timeout=10)
        response.raise_for_status()
        return response.content

    def _fetch_article_publish_date(self, article_url: str) -> str | None:
        """Fetch the real publication date from an article page.

        The listing page shows "recently featured" dates, but the article page
        shows the actual publication date. Looks for specific date element first
        (cover__text--date class with "Month DD, YYYY" format), falls back to
        <time> element.
        """
        try:
            response = util.fetch(article_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            date_elem = soup.find(class_='cover__text--date')
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                parsed = _parse_date_string(date_text)
                if parsed:
                    return parsed

            time_elem = soup.find('time')
            if time_elem:
                datetime_attr = time_elem.get('datetime', '').strip()
                return _parse_date_string(datetime_attr)
        except Exception as e:
            logger.warning(f"Could not fetch date from {article_url}: {e}")
        return None

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch blog posts for a specific date from blog listing page.

        The listing page shows "recently featured" dates, not original publication
        dates. For each article, we fetch its page to get the real publish date
        and filter by that.

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

        logger.info(f"Fetching articles for {target_month_year} (excluding {len(excluded_urls)} URLs)")

        try:
            page_content = self._fetch_page()
            soup = BeautifulSoup(page_content, 'html.parser')
            article_cards = soup.find_all('article', class_='card-blog')

            logger.info(f"Found {len(article_cards)} total articles on blog page")

            for card in article_cards:
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

                real_publish_date = self._fetch_article_publish_date(full_url)
                if not real_publish_date:
                    continue

                real_month_year = datetime.fromisoformat(real_publish_date).strftime("%B %Y")
                if real_month_year != target_month_year:
                    continue

                article = self._card_to_article(card, real_publish_date)
                if article:
                    articles.append(article)

            logger.info(f"Found {len(articles)} articles actually published in {target_month_year}")

        except Exception as e:
            logger.error(f"Error fetching blog: {e}", exc_info=True)

        issues = []
        if articles:
            first_of_month = target_date.replace(day=1).strftime("%Y-%m-%d")
            issues.append({
                'date': first_of_month,
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
