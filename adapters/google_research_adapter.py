"""
Google Research blog adapter using archive page HTML scraping.

This adapter fetches Google Research blog posts from year/month archive pages,
filters by exact publication date, and extracts article tags as metadata.
"""

import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("google_research_adapter")


def _parse_publication_date(date_text: str) -> str | None:
    """Parse a Google Research card date into ISO format.

    >>> _parse_publication_date("April 9, 2026")
    '2026-04-09'
    >>> _parse_publication_date("Invalid") is None
    True
    """
    try:
        return datetime.strptime(date_text.strip(), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


class GoogleResearchAdapter(NewsletterAdapter):
    """Adapter for the Google Research blog."""

    def __init__(self, config):
        super().__init__(config)
        self.blog_base_url = "https://research.google/blog"

    def _build_archive_url(self, target_date: datetime, page_number: int) -> str:
        archive_url = (
            f"{self.blog_base_url}/{target_date.year}/{target_date.month:02d}"
        )
        if page_number == 1:
            return archive_url
        return f"{archive_url}?page={page_number}"

    @util.retry()
    def _fetch_archive_page(self, archive_url: str) -> str:
        response = util.fetch(archive_url, timeout=10)
        response.raise_for_status()
        return response.text

    def _extract_total_pages(self, soup: BeautifulSoup) -> int:
        pagination_form = soup.select_one(".pagination__form[data-max-pages]")
        if pagination_form is None:
            return 1

        total_pages_text = pagination_form.get("data-max-pages", "").strip()
        if not total_pages_text:
            return 1

        try:
            return max(1, int(total_pages_text))
        except ValueError:
            logger.warning("Invalid total page count: %s", total_pages_text)
            return 1

    def _extract_article_cards(self, soup: BeautifulSoup) -> list:
        blog_grid = soup.select_one("section.blog-posts-grid")
        if blog_grid is None:
            return []

        return blog_grid.select("ul.blog-posts-grid__cards > li > a.glue-card")

    def _extract_tags(self, card) -> list[str]:
        tags: list[str] = []
        for tag_item in card.select(".glue-card__link-list__item"):
            raw_tag = tag_item.get_text(" ", strip=True)
            cleaned_tag = re.sub(r"\s*·\s*$", "", raw_tag).strip()
            if cleaned_tag:
                tags.append(cleaned_tag)
        return tags

    def _card_to_article(self, card, target_date_str: str) -> dict | None:
        title_element = card.select_one(".headline-5")
        date_element = card.select_one(".glue-card__content p.glue-label")
        if title_element is None or date_element is None:
            return None

        parsed_date = _parse_publication_date(date_element.get_text(strip=True))
        if parsed_date != target_date_str:
            return None

        href = card.get("href", "").strip()
        if not href:
            return None

        article_url = urljoin(self.config.base_url, href)
        article_title = title_element.get_text(" ", strip=True)
        if not article_title:
            return None

        article_tags = self._extract_tags(card)
        article_metadata = " · ".join(article_tags)

        return {
            "title": article_title,
            "article_meta": article_metadata,
            "url": article_url,
            "category": self.config.category_display_names.get(
                "blog", "Google Research Blog"
            ),
            "date": target_date_str,
            "newsletter_type": "blog",
            "removed": False,
        }

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch Google Research blog posts for an exact date."""
        articles: list[dict] = []
        excluded_set = set(excluded_urls)

        target_date = datetime.fromisoformat(util.format_date_for_url(date))
        target_date_str = target_date.strftime("%Y-%m-%d")
        total_pages = 1

        logger.info(
            "Fetching Google Research articles for %s (excluding %s URLs)",
            target_date_str,
            len(excluded_urls),
        )

        try:
            page_number = 1
            while page_number <= total_pages:
                archive_url = self._build_archive_url(target_date, page_number)
                page_html = self._fetch_archive_page(archive_url)
                soup = BeautifulSoup(page_html, "html.parser")

                if page_number == 1:
                    total_pages = self._extract_total_pages(soup)

                article_cards = self._extract_article_cards(soup)
                logger.info(
                    "Fetched Google Research archive page=%s/%s cards=%s url=%s",
                    page_number,
                    total_pages,
                    len(article_cards),
                    archive_url,
                )

                for card in article_cards:
                    article = self._card_to_article(card, target_date_str)
                    if article is None:
                        continue

                    canonical_url = util.canonicalize_url(article["url"])
                    if canonical_url in excluded_set:
                        continue

                    article["url"] = canonical_url
                    articles.append(article)

                page_number += 1

        except Exception as error:
            logger.error(
                "Error fetching Google Research archive for %s: %s",
                target_date_str,
                error,
                exc_info=True,
            )

        issues = []
        if articles:
            issues.append(
                {
                    "date": target_date_str,
                    "source_id": self.config.source_id,
                    "category": self.config.category_display_names.get(
                        "blog", "Google Research Blog"
                    ),
                    "title": None,
                    "subtitle": None,
                }
            )

        return self._normalize_response(articles, issues)
