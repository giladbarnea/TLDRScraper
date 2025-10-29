"""
Newsletter source configuration schema and registered sources.

This module defines the declarative configuration for newsletter sources,
enabling the addition of new sources without modifying core scraper logic.
"""

from dataclasses import dataclass


@dataclass
class NewsletterSourceConfig:
    """Configuration for a newsletter source."""

    source_id: str  # Unique identifier: "tldr_tech", "tldr_ai", "hackernews"
    display_name: str  # Human-readable name: "TLDR Tech", "Hacker News Daily"
    base_url: str  # Base URL: "https://tldr.tech"
    url_pattern: str  # URL template: "{base_url}/{type}/{date}"
    types: list[str]  # Subtypes within source: ["tech", "ai"] or ["daily"]
    user_agent: str  # User-Agent header (neutral default)

    # Parsing rules
    article_pattern: str  # Regex to identify articles
    section_emoji_enabled: bool  # Does this source use emoji sections?

    # Display preferences
    category_display_names: dict[str, str]  # {"tech": "TLDR Tech"}
    sort_order: int  # For multi-source ordering (lower = higher priority)
    color_theme: str | None = None  # UI theming (future enhancement)


# Registered newsletter sources
NEWSLETTER_CONFIGS = {
    "tldr_tech": NewsletterSourceConfig(
        source_id="tldr_tech",
        display_name="TLDR Tech",
        base_url="https://tldr.tech",
        url_pattern="{base_url}/tech/{date}",
        types=["tech"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern=r"\((\d+)\s+minute\s+read\)|\(GitHub\s+Repo\)",
        section_emoji_enabled=True,
        category_display_names={"tech": "TLDR Tech"},
        sort_order=2,
    ),
    "tldr_ai": NewsletterSourceConfig(
        source_id="tldr_ai",
        display_name="TLDR AI",
        base_url="https://tldr.tech",
        url_pattern="{base_url}/ai/{date}",
        types=["ai"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern=r"\((\d+)\s+minute\s+read\)|\(GitHub\s+Repo\)",
        section_emoji_enabled=True,
        category_display_names={"ai": "TLDR AI"},
        sort_order=1,  # AI comes before Tech
    ),
    "hackernews": NewsletterSourceConfig(
        source_id="hackernews",
        display_name="Hacker News",
        base_url="http://hn.algolia.com/api/v1",  # Using Algolia HN Search API
        url_pattern="",  # Not used (Algolia API-based)
        types=["top", "ask", "show"],  # Combined in single query via Algolia
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",  # Not used for API-based sources
        section_emoji_enabled=False,  # HackerNews doesn't have sections
        category_display_names={
            "top": "HN Top",
            "ask": "HN Ask",
            "show": "HN Show",
        },
        sort_order=3,  # After TLDR AI (1) and TLDR Tech (2)
    ),
}
