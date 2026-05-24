"""
Abstract base class for newsletter source adapters.

This module defines the interface that all newsletter adapters must implement,
providing a template method pattern for fetching, parsing, and normalizing
newsletter content from different sources.
"""

from bs4 import BeautifulSoup
import html2text

from newsletter_config import NewsletterSourceConfig
import util


class NewsletterAdapter:
    """Base adapter for newsletter sources.

    Subclasses can either:
    1. Implement fetch_issue and parse_articles for HTML-based sources
    2. Override scrape_date() entirely for API-based sources or custom workflows
    """

    def __init__(self, config: NewsletterSourceConfig):
        """Initialize adapter with source configuration.

        Args:
            config: Configuration object defining source-specific settings
        """
        self.config = config
        # Configure html2text for optimal conversion
        self.h = html2text.HTML2Text()
        self.h.body_width = 0  # Don't wrap lines
        self.h.unicode_snob = True  # Use unicode instead of ASCII approximations
        self.h.ignore_images = True  # Skip images, we only need text
        self.h.protect_links = True  # Don't wrap URLs
        self.h.single_line_break = True  # Use single line breaks

    def fetch_issue(self, date: str, newsletter_type: str) -> str | None:
        """Fetch raw HTML for a specific issue.

        Override this method for HTML-based sources.
        For API-based sources, override scrape_date() instead.

        Args:
            date: Date string in format used by source
            newsletter_type: Type/category within source (e.g., "tech", "ai")

        Returns:
            HTML content as string, or None if issue not found
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement fetch_issue() or override scrape_date()"
        )

    def parse_articles(
        self, markdown: str, date: str, newsletter_type: str
    ) -> list[dict]:
        """Parse articles from markdown content.

        Override this method for HTML-based sources.
        For API-based sources, override scrape_date() instead.

        Args:
            markdown: Converted markdown content
            date: Date string for the issue
            newsletter_type: Type/category within source

        Returns:
            List of article dictionaries with keys: title, url, category, date, etc.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement parse_articles() or override scrape_date()"
        )

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Template method - orchestrates fetch + parse + normalize.

        This default implementation follows the HTML scraping workflow:
        1. Fetch HTML for each type configured for this source
        2. Convert HTML to markdown
        3. Parse articles
        4. Filter out excluded URLs
        5. Normalize response with source_id

        Subclasses can override this entire method for different workflows
        (e.g., API-based sources that don't use HTML conversion).
        """
        articles = []
        excluded_set = set(excluded_urls)

        for newsletter_type in self.config.types:
            html = self.fetch_issue(date, newsletter_type)
            if html is None:
                continue

            markdown = self._html_to_markdown(html)
            parsed_articles = self.parse_articles(markdown, date, newsletter_type)

            for article in parsed_articles:
                canonical_url = util.canonicalize_url(article['url'])
                if canonical_url not in excluded_set:
                    articles.append(article)

        return self._normalize_response(articles)

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to markdown using BeautifulSoup and html2text.

        Args:
            html: Raw HTML content

        Returns:
            Markdown string
        """
        soup = BeautifulSoup(html, "html.parser")
        newsletter_content = soup.body or soup
        content_html = str(newsletter_content)
        return self.h.handle(content_html)

    def _normalize_response(self, articles: list[dict]) -> dict:
        """Stamp every article with source_id so multi-source aggregations stay unambiguous."""
        return {
            "source_id": self.config.source_id,
            "articles": [
                {**article, "source_id": self.config.source_id} for article in articles
            ],
        }
