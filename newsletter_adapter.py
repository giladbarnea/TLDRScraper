"""
Abstract base class for newsletter source adapters.

This module defines the interface that all newsletter adapters must implement,
providing a template method pattern for fetching, parsing, and normalizing
newsletter content from different sources.
"""

from abc import ABC, abstractmethod
from io import BytesIO

from bs4 import BeautifulSoup
from markitdown import MarkItDown

from newsletter_config import NewsletterSourceConfig
import util


class NewsletterAdapter(ABC):
    """Abstract adapter for newsletter sources.

    Subclasses must implement fetch_issue, parse_articles, and extract_issue_metadata
    to provide source-specific logic for their newsletter format.
    """

    def __init__(self, config: NewsletterSourceConfig):
        """Initialize adapter with source configuration.

        Args:
            config: Configuration object defining source-specific settings
        """
        self.config = config
        self.md = MarkItDown()

    @abstractmethod
    def fetch_issue(self, date: str, newsletter_type: str) -> str | None:
        """Fetch raw HTML for a specific issue.

        Args:
            date: Date string in format used by source
            newsletter_type: Type/category within source (e.g., "tech", "ai")

        Returns:
            HTML content as string, or None if issue not found
        """
        pass

    @abstractmethod
    def parse_articles(
        self, markdown: str, date: str, newsletter_type: str
    ) -> list[dict]:
        """Parse articles from markdown content.

        Args:
            markdown: Converted markdown content
            date: Date string for the issue
            newsletter_type: Type/category within source

        Returns:
            List of article dictionaries with keys: title, url, category, date, etc.
        """
        pass

    @abstractmethod
    def extract_issue_metadata(
        self, markdown: str, date: str, newsletter_type: str
    ) -> dict | None:
        """Extract issue metadata (title, subtitle, sections).

        Args:
            markdown: Converted markdown content
            date: Date string for the issue
            newsletter_type: Type/category within source

        Returns:
            Dictionary with issue metadata, or None if no metadata found
        """
        pass

    def scrape_date(self, date: str) -> dict:
        """Template method - orchestrates fetch + parse + normalize.

        This method implements the overall scraping workflow:
        1. Fetch HTML for each type configured for this source
        2. Convert HTML to markdown
        3. Parse articles and extract metadata
        4. Normalize response with source_id

        Args:
            date: Date string to scrape

        Returns:
            Normalized response dictionary with source_id, articles, and issues
        """
        articles = []
        issues = []

        for newsletter_type in self.config.types:
            # Fetch raw HTML
            html = self.fetch_issue(date, newsletter_type)
            if html is None:
                continue

            # Convert to markdown
            markdown = self._html_to_markdown(html)

            # Parse articles and metadata
            parsed_articles = self.parse_articles(markdown, date, newsletter_type)
            articles.extend(parsed_articles)

            issue_meta = self.extract_issue_metadata(markdown, date, newsletter_type)
            if issue_meta:
                issues.append(issue_meta)

        return self._normalize_response(articles, issues)

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to markdown using BeautifulSoup and MarkItDown.

        Args:
            html: Raw HTML content

        Returns:
            Markdown string
        """
        soup = BeautifulSoup(html, "html.parser")
        newsletter_content = soup.body or soup
        content_html = str(newsletter_content)
        content_stream = BytesIO(content_html.encode("utf-8"))
        result = self.md.convert_stream(content_stream, file_extension=".html")
        return result.text_content

    def _normalize_response(self, articles: list[dict], issues: list[dict]) -> dict:
        """Convert to standardized format with source_id.

        This ensures every article and issue includes the source_id to prevent
        identity collisions when multiple sources are aggregated.

        Args:
            articles: List of parsed articles
            issues: List of parsed issue metadata

        Returns:
            Normalized response with source_id added to all items
        """
        return {
            "source_id": self.config.source_id,
            "articles": [
                {**article, "source_id": self.config.source_id} for article in articles
            ],
            "issues": [
                {**issue, "source_id": self.config.source_id} for issue in issues
            ],
        }
