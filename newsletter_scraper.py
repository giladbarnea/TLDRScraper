import logging
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    elif config.source_id == "aiwithmike":
        from adapters.aiwithmike_adapter import AiWithMikeAdapter
        return AiWithMikeAdapter(config)
    elif config.source_id == "savannah_ostrowski":
        from adapters.savannah_adapter import SavannahAdapter
        return SavannahAdapter(config)
    elif config.source_id == "lucumr":
        from adapters.lucumr_adapter import LucumrAdapter
        return LucumrAdapter(config)
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
    """Sort issues by date DESC, then randomize with subtle priority weighting.

    Within each date, newsletters are shuffled randomly but lower sort_order
    (rarer sources) have a slight preference to appear earlier.

    >>> issues = [{"date": "2024-01-01", "source_id": "tldr_tech", "category": "Tech"}]
    >>> result = _sort_issues(issues)
    >>> len(result) == 1
    True
    """
    import random

    max_sort_order = max(
        config.sort_order for config in NEWSLETTER_CONFIGS.values()
    )
    priority_weight = 0.15

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
            else max_sort_order
        )

        normalized_priority = sort_order / max_sort_order
        weighted_random = (1 - priority_weight) * random.random() + priority_weight * normalized_priority

        return (-date_ordinal, weighted_random)

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






def _collect_newsletters_for_date_from_source_worker(
    source_id,
    config,
    date,
    date_str,
    excluded_urls,
):
    """Worker function for parallel scraping that returns results instead of mutating shared state.

    Args:
        source_id: Source identifier
        config: NewsletterSourceConfig instance
        date: Date object
        date_str: Date string
        excluded_urls: List of canonical URLs to exclude

    Returns:
        dict with keys:
            - articles: List of article dicts with canonical URLs
            - issues: List of issue metadata dicts
            - network_articles: Count of new articles fetched
            - error: Error message if any, otherwise None
            - source_id: Source identifier for tracking
    """
    result = {
        "articles": [],
        "issues": [],
        "network_articles": 0,
        "error": None,
        "source_id": source_id,
    }

    try:
        adapter = _get_adapter_for_source(config)
        scrape_result = adapter.scrape_date(date, excluded_urls)

        # Process articles - canonicalize URLs
        for article in scrape_result.get("articles", []):
            canonical_url = util.canonicalize_url(article["url"])
            article["url"] = canonical_url
            result["articles"].append(article)

        # Process issues - deep copy to avoid shared state issues
        for issue in scrape_result.get("issues", []):
            issue_copy = json.loads(json.dumps(issue))
            result["issues"].append(issue_copy)

        result["network_articles"] = len(result["articles"])

    except Exception as e:
        logger.error(
            f"Error processing {config.display_name} for {date_str}: {e}",
            exc_info=True,
        )
        result["error"] = str(e)

    return result


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
        f"Processing {config.display_name} for {date_str} ({current_processed}/{total_count})",
    )

    try:
        # Get adapter and scrape
        adapter = _get_adapter_for_source(config)
        result = adapter.scrape_date(date, excluded_urls)

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
            f"Error processing {config.display_name} for {date_str}: {e}",
            exc_info=True,
        )

    return current_processed, network_articles


def _scrape_sources_for_date_parallel(
    date,
    date_str,
    source_ids,
    excluded_urls,
    max_workers=8,
):
    """Execute all sources for a date in parallel using thread pool.

    Args:
        date: Date object
        date_str: Date string
        source_ids: List of source IDs to scrape
        excluded_urls: List of canonical URLs to exclude
        max_workers: Maximum number of parallel workers

    Returns:
        List of tuples (source_id, result_dict) in original source_ids order
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_source = {}
        for source_id in source_ids:
            if source_id not in NEWSLETTER_CONFIGS:
                logger.warning(f"Unknown source_id: {source_id}, skipping")
                continue

            config = NEWSLETTER_CONFIGS[source_id]
            future = executor.submit(
                _collect_newsletters_for_date_from_source_worker,
                source_id,
                config,
                date,
                date_str,
                excluded_urls,
            )
            future_to_source[future] = source_id

        # Collect results maintaining original order
        source_to_result = {}
        for future in as_completed(future_to_source):
            source_id = future_to_source[future]
            try:
                result = future.result(timeout=60)
                source_to_result[source_id] = result
            except Exception as e:
                logger.error(f"Failed to get result for {source_id} on {date_str}: {e}")
                source_to_result[source_id] = {
                    "articles": [],
                    "issues": [],
                    "network_articles": 0,
                    "error": str(e),
                    "source_id": source_id,
                }

    # Return results in original source_ids order for determinism
    for source_id in source_ids:
        if source_id in source_to_result:
            results.append((source_id, source_to_result[source_id]))

    return results


def _merge_source_results_deterministically(
    source_results,
    date_str,
    url_set,
    all_articles,
    issue_metadata_by_key,
):
    """Merge results from parallel sources maintaining deterministic ordering.

    Args:
        source_results: List of (source_id, result_dict) tuples in deterministic order
        date_str: Date string for issue metadata keying
        url_set: Set for URL deduplication (mutated)
        all_articles: List to append articles to (mutated)
        issue_metadata_by_key: Dict for issue metadata (mutated)

    Returns:
        Tuple of (total_new_articles, total_network_articles)
    """
    total_new_articles = 0
    total_network_articles = 0

    # Process in original source order to maintain determinism
    for source_id, result in source_results:
        if result.get("error"):
            logger.warning(f"Skipping {source_id} due to error: {result['error']}")
            continue

        # Merge articles with deduplication
        for article in result["articles"]:
            canonical_url = article["url"]
            if canonical_url not in url_set:
                url_set.add(canonical_url)
                all_articles.append(article)
                total_new_articles += 1

        # Merge issues (no deduplication needed due to triple-key design)
        for issue in result["issues"]:
            issue_source_id = issue.get("source_id", "")
            category = issue.get("category", "")
            key = (date_str, issue_source_id, category)
            issue_metadata_by_key[key] = issue

        total_network_articles += result.get("network_articles", 0)

    return total_new_articles, total_network_articles


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

    # Check for parallel scraping environment variable (default: enabled)
    use_parallel = util.resolve_env_var("ENABLE_PARALLEL_SCRAPING", default="true").lower() in ("true", "1", "yes")
    max_workers = int(util.resolve_env_var("SCRAPER_MAX_WORKERS", default="8"))

    for date in dates:
        date_str = util.format_date_for_url(date)

        if use_parallel:
            # Parallel execution: all sources for this date run concurrently
            logger.info(f"Scraping {len(source_ids)} sources for {date_str} in parallel (max_workers={max_workers})")
            source_results = _scrape_sources_for_date_parallel(
                date, date_str, source_ids, excluded_urls, max_workers
            )

            # Merge results deterministically
            new_articles, network_increment = _merge_source_results_deterministically(
                source_results, date_str, url_set, all_articles, issue_metadata_by_key
            )

            processed_count += len(source_results)
            network_fetches += network_increment

            logger.info(
                f"Date {date_str}: {len(source_results)} sources processed, "
                f"{new_articles} new articles ({processed_count}/{total_count} total)"
            )
        else:
            # Sequential execution (legacy/fallback)
            for source_id in source_ids:
                if source_id not in NEWSLETTER_CONFIGS:
                    logger.warning(
                        f"Unknown source_id: {source_id}, skipping",
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
