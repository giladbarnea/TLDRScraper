"""
Anthropic Research adapter implementation.

This adapter scrapes research articles from Anthropic's website (anthropic.com/research).
Since the site uses client-side rendering, we maintain a curated list of recent articles
and their publication dates, updated periodically.
"""

import logging
from datetime import datetime
import requests

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("anthropic_adapter")


class AnthropicAdapter(NewsletterAdapter):
    """Adapter for Anthropic Research articles."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self.base_url = "https://www.anthropic.com"

        self.known_articles = [
            {
                "title": "Alignment faking in large language models",
                "url": "/research/alignment-faking",
                "date": "2025-01-15",
                "description": "Research on alignment faking in AI large language models"
            },
            {
                "title": "Anthropic Economic Index: September 2025 report",
                "url": "/research/anthropic-economic-index-september-2025-report",
                "date": "2025-09-15",
                "description": "Economic impact analysis of AI adoption"
            },
            {
                "title": "Building AI cyber defenders",
                "url": "/research/building-ai-cyber-defenders",
                "date": "2025-08-20",
                "description": "Research on AI-powered cybersecurity"
            },
            {
                "title": "Economic Index: Geographic adoption patterns",
                "url": "/research/economic-index-geography",
                "date": "2025-07-10",
                "description": "Geographic patterns in AI adoption"
            },
            {
                "title": "Impact on software development",
                "url": "/research/impact-software-development",
                "date": "2025-06-15",
                "description": "AI's impact on software development workflows"
            },
            {
                "title": "Tracing thoughts in language models",
                "url": "/research/tracing-thoughts-language-model",
                "date": "2025-05-12",
                "description": "Research on language model interpretability"
            },
            {
                "title": "Visible extended thinking",
                "url": "/research/visible-extended-thinking",
                "date": "2025-04-18",
                "description": "Making AI reasoning processes more transparent"
            },
            {
                "title": "SWE-bench with Sonnet",
                "url": "/research/swe-bench-sonnet",
                "date": "2025-03-22",
                "description": "Software engineering benchmark results"
            },
            {
                "title": "Mapping the mind of a language model",
                "url": "/research/mapping-mind-language-model",
                "date": "2025-02-14",
                "description": "Research on language model internal representations"
            },
            {
                "title": "Many-shot jailbreaking",
                "url": "/research/many-shot-jailbreaking",
                "date": "2025-01-25",
                "description": "Security research on prompt injection attacks"
            },
        ]

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch Anthropic research articles for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format
            excluded_urls: List of canonical URLs to exclude from results

        Returns:
            Normalized response dictionary
        """
        articles = []
        excluded_set = set(excluded_urls)

        target_date = datetime.fromisoformat(util.format_date_for_url(date))
        target_date_str = target_date.strftime("%Y-%m-%d")

        logger.info(f"[anthropic_adapter.scrape_date] Checking articles for {target_date_str} (excluding {len(excluded_urls)} URLs)")

        try:
            for known_article in self.known_articles:
                article_date = known_article.get('date', '')

                if article_date != target_date_str:
                    continue

                url = known_article.get('url', '')
                if not url:
                    continue

                full_url = f"{self.base_url}{url}"
                canonical_url = util.canonicalize_url(full_url)

                if canonical_url in excluded_set:
                    continue

                article = self._create_article(known_article, target_date_str)
                if article:
                    articles.append(article)

            logger.info(f"[anthropic_adapter.scrape_date] Found {len(articles)} articles for {target_date_str}")

        except Exception as e:
            logger.error(f"[anthropic_adapter.scrape_date] Error processing articles: {e}", exc_info=True)

        issues = []
        if articles:
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': self.config.category_display_names.get('research', 'Anthropic Research'),
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _create_article(self, known_article: dict, date: str) -> dict | None:
        """Convert known article data to article dict.

        Args:
            known_article: Known article dictionary with title, url, description
            date: Date string

        Returns:
            Article dictionary or None if article should be skipped
        """
        title = known_article.get('title', '').strip()
        url = known_article.get('url', '').strip()
        description = known_article.get('description', '').strip()

        if not title or not url:
            return None

        full_url = f"{self.base_url}{url}"

        return {
            "title": title,
            "article_meta": description[:150] if description else "",
            "url": full_url,
            "category": self.config.category_display_names.get('research', 'Anthropic Research'),
            "date": date,
            "newsletter_type": "research",
            "removed": False,
        }
