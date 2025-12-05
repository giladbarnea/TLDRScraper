import logging
import json
import time
from datetime import datetime

from newsletter_config import NEWSLETTER_CONFIGS
from adapters.tldr_adapter import TLDRAdapter
from newsletter_merger import build_markdown_output

import util

logger = logging.getLogger("newsletter_scraper")


def _get_adapter_for_source(config):
    """Factory pattern - returns appropriate adapter for source.

    Args:
        config: NewsletterSourceConfig instance

    Returns:
        NewsletterAdapter instance

    Raises:
        ValueError: If no adapter exists for the source
    """
    if config.source_id.startswith("tldr_"):
        return TLDRAdapter(config)
    elif config.source_id == "hackernews":
        from adapters.hackernews_adapter import HackerNewsAdapter
        return HackerNewsAdapter(config)
    elif config.source_id == "xeiaso":
        from adapters.xeiaso_adapter import XeIasoAdapter
        return XeIasoAdapter(config)
    elif config.source_id == "simon_willison":
        from adapters.simon_willison_adapter import SimonWillisonAdapter
        return SimonWillisonAdapter(config)
    elif config.source_id == "danluu":
        from adapters.danluu_adapter import DanLuuAdapter
        return DanLuuAdapter(config)
    elif config.source_id == "will_larson":
        from adapters.will_larson_adapter import WillLarsonAdapter
        return WillLarsonAdapter(config)
    elif config.source_id == "lenny_newsletter":
        from adapters.lenny_newsletter_adapter import LennyNewsletterAdapter
        return LennyNewsletterAdapter(config)
    elif config.source_id == "pragmatic_engineer":
        from adapters.pragmatic_engineer_adapter import PragmaticEngineerAdapter
        return PragmaticEngineerAdapter(config)
    elif config.source_id == "cloudflare":
        from adapters.cloudflare_adapter import CloudflareAdapter
        return CloudflareAdapter(config)
    elif config.source_id == "jessitron":
        from adapters.jessitron_adapter import JessitronAdapter
        return JessitronAdapter(config)
    elif config.source_id == "stripe_engineering":
        from adapters.stripe_engineering_adapter import StripeEngineeringAdapter
        return StripeEngineeringAdapter(config)
    elif config.source_id == "deepmind":
        from adapters.deepmind_adapter import DeepMindAdapter
        return DeepMindAdapter(config)
    elif config.source_id == "pointer":
        from adapters.pointer_adapter import PointerAdapter
        return PointerAdapter(config)
    elif config.source_id == "softwareleadweekly":
        from adapters.softwareleadweekly_adapter import SoftwareLeadWeeklyAdapter
        return SoftwareLeadWeeklyAdapter(config)
    elif config.source_id == "anthropic":
        from adapters.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter(config)
    elif config.source_id == "netflix":
        from adapters.netflix_adapter import NetflixAdapter
        return NetflixAdapter(config)
    elif config.source_id == "hillel_wayne":
        from adapters.hillel_wayne_adapter import HillelWayneAdapter
        return HillelWayneAdapter(config)
    elif config.source_id == "infoq":
        from adapters.infoq_adapter import InfoQAdapter
        return InfoQAdapter(config)
    elif config.source_id == "bytebytego":
        from adapters.bytebytego_adapter import ByteByteGoAdapter
        return ByteByteGoAdapter(config)
    elif config.source_id == "martin_fowler":
        from adapters.martin_fowler_adapter import MartinFowlerAdapter
        return MartinFowlerAdapter(config)
    elif config.source_id == "react_status":
        from adapters.react_status_adapter import ReactStatusAdapter
        return ReactStatusAdapter(config)
    elif config.source_id == "node_weekly":
        from adapters.node_weekly_adapter import NodeWeeklyAdapter
        return NodeWeeklyAdapter(config)
    else:
        raise ValueError(f"No adapter registered for source: {config.source_id}")


def _normalize_article_payload(article: dict) -> dict:
    """Normalize article dict into API payload format.

    >>> article = {"url": "https://example.com", "title": "Test", "date": "2024-01-01", "category": "Tech", "removed": None}
    >>> result = _normalize_article_payload(article)
    >>> result["removed"]
    False
    """
    payload = {
        "url": article["url"],
        "title": article["title"],
        "article_meta": article.get("article_meta", ""),
        "date": article["date"],
        "category": article["category"],
        "removed": bool(article.get("removed", False)),
    }

    if article.get("source_id"):
        payload["source_id"] = article["source_id"]
    if article.get("section_title"):
        payload["section_title"] = article["section_title"]
    if article.get("section_emoji"):
        payload["section_emoji"] = article["section_emoji"]
    if article.get("section_order") is not None:
        payload["section_order"] = article["section_order"]
    if article.get("newsletter_type"):
        payload["newsletter_type"] = article["newsletter_type"]

    return payload


def _group_articles_by_date(articles: list[dict]) -> dict[str, list[dict]]:
    """Group articles by date string.

    >>> articles = [{"date": "2024-01-01", "title": "Test"}]
    >>> result = _group_articles_by_date(articles)
    >>> "2024-01-01" in result
    True
    """
    grouped_articles: dict[str, list[dict]] = {}
    for article in articles:
        date_value = article["date"]
        if isinstance(date_value, str):
            article_date = date_value
        else:
            article_date = util.format_date_for_url(date_value)

        grouped_articles.setdefault(article_date, []).append(article)

    return grouped_articles


def _sort_issues(issues: list[dict]) -> list[dict]:
    """Sort issues by date DESC, source sort_order ASC, category ASC.

    >>> issues = [{"date": "2024-01-01", "source_id": "tldr_tech", "category": "Tech"}]
    >>> result = _sort_issues(issues)
    >>> len(result) == 1
    True
    """
    def _issue_sort_key(issue: dict) -> tuple:
        date_text = issue.get("date", "") or ""
        try:
            date_ordinal = datetime.fromisoformat(date_text).toordinal()
        except Exception:
            date_ordinal = 0

        source_id = issue.get("source_id")
        sort_order = (
            NEWSLETTER_CONFIGS[source_id].sort_order
            if source_id in NEWSLETTER_CONFIGS
            else 999
        )

        return (-date_ordinal, sort_order, issue.get("category", ""))

    return sorted(issues, key=_issue_sort_key)


def _compute_stats(
    articles: list[dict],
    url_set: set[str],
    dates: list,
    grouped_articles: dict[str, list[dict]],
    network_fetches: int,
) -> dict:
    """Compute scrape statistics.

    >>> stats = _compute_stats([], set(), [], {}, 0)
    >>> stats["total_articles"]
    0
    """
    return {
        "total_articles": len(articles),
        "unique_urls": len(url_set),
        "dates_processed": len(dates),
        "dates_with_content": len(grouped_articles),
        "network_fetches": network_fetches,
        "cache_mode": "read_write",
    }


def _build_scrape_response(
    start_date,
    end_date,
    dates,
    all_articles,
    url_set,
    issue_metadata_by_key,
    network_fetches,
):
    """Orchestrate building the complete scrape response."""
    articles_data = [_normalize_article_payload(a) for a in all_articles]
    grouped_articles = _group_articles_by_date(all_articles)
    output = build_markdown_output(
        start_date, end_date, grouped_articles, issue_metadata_by_key
    )
    issues_output = _sort_issues(list(issue_metadata_by_key.values()))
    stats = _compute_stats(
        all_articles, url_set, dates, grouped_articles, network_fetches
    )

    return {
        "success": True,
        "output": output,
        "articles": articles_data,
        "issues": issues_output,
        "stats": stats,
    }






def _collect_newsletters_for_date_from_source(
    source_id,
    config,
    date,
    date_str,
    processed_count,
    total_count,
    url_set,
    all_articles,
    issue_metadata_by_key,
    excluded_urls,
):
    """Collect newsletters for a date using source adapter.

    Args:
        source_id: Source identifier
        config: NewsletterSourceConfig instance
        date: Date object
        date_str: Date string
        processed_count: Current progress counter
        total_count: Total items to process
        url_set: Set of URLs for deduplication
        all_articles: List to append articles to
        issue_metadata_by_key: Dict to store issue metadata
        excluded_urls: List of canonical URLs to exclude

    Returns:
        Tuple of (updated_processed_count, network_articles_count)
    """
    day_articles: list[dict] = []
    network_articles = 0
    current_processed = processed_count

    current_processed += 1
    logger.info(
        f"[newsletter_scraper] Processing {config.display_name} for {date_str} ({current_processed}/{total_count})",
    )

    try:
        # Get adapter and scrape
        adapter = _get_adapter_for_source(config)
        result = adapter.scrape_date(date_str, excluded_urls)

        # Process articles from response
        for article in result.get("articles", []):
            canonical_url = util.canonicalize_url(article["url"])
            article["url"] = canonical_url

            day_articles.append(article)

            if canonical_url not in url_set:
                url_set.add(canonical_url)
                all_articles.append(article)
                network_articles += 1

        # Process issues from response
        for issue in result.get("issues", []):
            issue_copy = json.loads(json.dumps(issue))
            source_id = issue_copy.get("source_id", "")
            category = issue_copy.get("category", "")
            # Use triple-key to prevent collisions
            issue_metadata_by_key[(date_str, source_id, category)] = issue_copy

        # Rate limiting
        if network_articles > 0:
            time.sleep(0.2)

    except Exception as e:
        logger.error(
            f"[newsletter_scraper] Error processing {config.display_name} for {date_str}: {e}",
            exc_info=True,
        )

    return current_processed, network_articles


def scrape_date_range(start_date, end_date, source_ids=None, excluded_urls=None):
    """Scrape newsletters in date range using configured adapters.

    Args:
        start_date: Start date
        end_date: End date
        source_ids: Optional list of source IDs to scrape. If None, scrapes all configured sources.
        excluded_urls: List of canonical URLs to exclude from results

    Returns:
        Response dictionary with articles and issues
    """
    dates = util.get_date_range(start_date, end_date)

    # Default to all configured sources
    if source_ids is None:
        source_ids = list(NEWSLETTER_CONFIGS.keys())

    # Default to empty list for excluded URLs
    if excluded_urls is None:
        excluded_urls = []

    all_articles: list[dict] = []
    url_set: set[str] = set()
    processed_count = 0
    total_count = len(dates) * len(source_ids)
    network_fetches = 0
    issue_metadata_by_key: dict[tuple[str, str, str], dict] = {}  # (date, source_id, category)

    for date in dates:
        date_str = util.format_date_for_url(date)

        for source_id in source_ids:
            if source_id not in NEWSLETTER_CONFIGS:
                logger.warning(
                    f"[newsletter_scraper] Unknown source_id: {source_id}, skipping",
                )
                continue

            config = NEWSLETTER_CONFIGS[source_id]

            processed_count, network_increment = _collect_newsletters_for_date_from_source(
                source_id,
                config,
                date,
                date_str,
                processed_count,
                total_count,
                url_set,
                all_articles,
                issue_metadata_by_key,
                excluded_urls,
            )
            network_fetches += network_increment

    # Ensure all articles have removed field
    for article in all_articles:
        article.setdefault("removed", False)

    return _build_scrape_response(
        start_date,
        end_date,
        dates,
        all_articles,
        url_set,
        issue_metadata_by_key,
        network_fetches,
    )
