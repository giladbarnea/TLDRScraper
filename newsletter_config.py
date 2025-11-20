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

    # Display preferences
    category_display_names: dict[str, str]  # {"tech": "TLDR Tech"}
    sort_order: int  # For multi-source ordering (lower = higher priority)


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
        category_display_names={
            "top": "HN Top",
            "ask": "HN Ask",
            "show": "HN Show",
        },
        sort_order=3,  # After TLDR AI (1) and TLDR Tech (2)
    ),
    "xeiaso": NewsletterSourceConfig(
        source_id="xeiaso",
        display_name="Xe Iaso",
        base_url="https://xeiaso.net",
        url_pattern="",
        types=["blog"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"blog": "Xe Iaso"},
        sort_order=4,
    ),
    "simon_willison": NewsletterSourceConfig(
        source_id="simon_willison",
        display_name="Simon Willison",
        base_url="https://simonwillison.net",
        url_pattern="",
        types=["blog"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"blog": "Simon Willison"},
        sort_order=5,
    ),
    "danluu": NewsletterSourceConfig(
        source_id="danluu",
        display_name="Dan Luu",
        base_url="https://danluu.com",
        url_pattern="",
        types=["blog"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"blog": "Dan Luu"},
        sort_order=5,
    ),
    "will_larson": NewsletterSourceConfig(
        source_id="will_larson",
        display_name="Irrational Exuberance",
        base_url="https://lethain.com",
        url_pattern="",
        types=["blog"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"blog": "Engineering Leadership"},
        sort_order=6,
    ),
    "cloudflare": NewsletterSourceConfig(
        source_id="cloudflare",
        display_name="Cloudflare Blog",
        base_url="https://blog.cloudflare.com",
        url_pattern="",
        types=["blog"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"blog": "Cloudflare Blog"},
        sort_order=7,
    ),
    "lenny_newsletter": NewsletterSourceConfig(
        source_id="lenny_newsletter",
        display_name="Lenny's Newsletter",
        base_url="https://www.lennysnewsletter.com",
        url_pattern="",
        types=["newsletter"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"newsletter": "Lenny's Newsletter"},
        sort_order=8,
    ),
    "pragmatic_engineer": NewsletterSourceConfig(
        source_id="pragmatic_engineer",
        display_name="The Pragmatic Engineer",
        base_url="https://newsletter.pragmaticengineer.com",
        url_pattern="",
        types=["newsletter"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"newsletter": "The Pragmatic Engineer"},
        sort_order=9,
    ),
    "jessitron": NewsletterSourceConfig(
        source_id="jessitron",
        display_name="Jessitron",
        base_url="https://jessitron.com",
        url_pattern="",
        types=["blog"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"blog": "Jessitron"},
        sort_order=10,
    ),
    "stripe_engineering": NewsletterSourceConfig(
        source_id="stripe_engineering",
        display_name="Stripe Engineering",
        base_url="https://stripe.com/blog/engineering",
        url_pattern="",
        types=["engineering"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"engineering": "Stripe Engineering"},
        sort_order=11,
    ),
    "deepmind": NewsletterSourceConfig(
        source_id="deepmind",
        display_name="Google DeepMind",
        base_url="https://deepmind.google",
        url_pattern="",
        types=["blog"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"blog": "Google DeepMind"},
        sort_order=12,
    ),
    "pointer": NewsletterSourceConfig(
        source_id="pointer",
        display_name="Pointer",
        base_url="https://www.pointer.io",
        url_pattern="",
        types=["newsletter"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"newsletter": "Pointer"},
        sort_order=13,
    ),
    "netflix": NewsletterSourceConfig(
        source_id="netflix",
        display_name="Netflix Tech Blog",
        base_url="https://medium.com/netflix-techblog",
        url_pattern="",
        types=["blog"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"blog": "Netflix Tech"},
        sort_order=13,
    ),
    "anthropic": NewsletterSourceConfig(
        source_id="anthropic",
        display_name="Anthropic Research",
        base_url="https://www.anthropic.com",
        url_pattern="",
        types=["research"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"research": "Anthropic Research"},
        sort_order=14,
    ),
    "softwareleadweekly": NewsletterSourceConfig(
        source_id="softwareleadweekly",
        display_name="Software Lead Weekly",
        base_url="https://softwareleadweekly.com",
        url_pattern="",
        types=["newsletter"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"newsletter": "Software Lead Weekly"},
        sort_order=8,
    ),
    "hillel_wayne": NewsletterSourceConfig(
        source_id="hillel_wayne",
        display_name="Hillel Wayne",
        base_url="https://www.hillelwayne.com",
        url_pattern="",
        types=["blog"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"blog": "Hillel Wayne"},
        sort_order=15,
    ),
    "infoq": NewsletterSourceConfig(
        source_id="infoq",
        display_name="InfoQ",
        base_url="https://www.infoq.com",
        url_pattern="",
        types=["articles"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern="",
        category_display_names={"articles": "InfoQ"},
        sort_order=16,
    ),
}
