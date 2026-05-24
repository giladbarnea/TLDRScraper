import logging

from newsletter_config import NEWSLETTER_CONFIGS
from adapters.tldr_adapter import TLDRAdapter
import storage_service

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
    elif config.source_id == "pragmatic_engineer":
        from adapters.pragmatic_engineer_adapter import PragmaticEngineerAdapter
        return PragmaticEngineerAdapter(config)
    elif config.source_id == "jessitron":
        from adapters.jessitron_adapter import JessitronAdapter
        return JessitronAdapter(config)
    elif config.source_id == "stripe_engineering":
        from adapters.stripe_engineering_adapter import StripeEngineeringAdapter
        return StripeEngineeringAdapter(config)
    elif config.source_id == "deepmind":
        from adapters.deepmind_adapter import DeepMindAdapter
        return DeepMindAdapter(config)
    elif config.source_id == "google_research":
        from adapters.google_research_adapter import GoogleResearchAdapter
        return GoogleResearchAdapter(config)
    elif config.source_id == "pointer":
        from adapters.pointer_adapter import PointerAdapter
        return PointerAdapter(config)
    elif config.source_id == "softwareleadweekly":
        from adapters.softwareleadweekly_adapter import SoftwareLeadWeeklyAdapter
        return SoftwareLeadWeeklyAdapter(config)
    elif config.source_id == "anthropic":
        from adapters.anthropic_adapter import AnthropicResearchAdapter
        return AnthropicResearchAdapter(config)
    elif config.source_id == "anthropic_news":
        from adapters.anthropic_news_adapter import AnthropicNewsAdapter
        return AnthropicNewsAdapter(config)
    elif config.source_id == "claude_blog":
        from adapters.claude_blog_adapter import ClaudeBlogAdapter
        return ClaudeBlogAdapter(config)
    elif config.source_id == "netflix":
        from adapters.netflix_adapter import NetflixAdapter
        return NetflixAdapter(config)
    elif config.source_id == "hillel_wayne":
        from adapters.hillel_wayne_adapter import HillelWayneAdapter
        return HillelWayneAdapter(config)
    elif config.source_id == "martin_fowler":
        from adapters.martin_fowler_adapter import MartinFowlerAdapter
        return MartinFowlerAdapter(config)
    elif config.source_id == "react_status":
        from adapters.react_status_adapter import ReactStatusAdapter
        return ReactStatusAdapter(config)
    elif config.source_id == "aiwithmike":
        from adapters.aiwithmike_adapter import AiWithMikeAdapter
        return AiWithMikeAdapter(config)
    elif config.source_id == "savannah_ostrowski":
        from adapters.savannah_adapter import SavannahAdapter
        return SavannahAdapter(config)
    elif config.source_id == "lucumr":
        from adapters.lucumr_adapter import LucumrAdapter
        return LucumrAdapter(config)
    elif config.source_id == "trendshift":
        from adapters.trendshift_adapter import TrendshiftAdapter
        return TrendshiftAdapter(config)
    else:
        raise ValueError(f"No adapter registered for source: {config.source_id}")


def get_default_source_ids() -> list[str]:
    """Return configured source IDs.

    >>> isinstance(get_default_source_ids(), list)
    True
    """
    return list(NEWSLETTER_CONFIGS.keys())


def scrape_single_source_for_date(
    date,
    source_id,
    excluded_urls,
):
    result = {
        "articles": [],
        "network_articles": 0,
        "error": None,
        "source_id": source_id,
    }
    date_str = util.format_date_for_url(date)

    if source_id not in NEWSLETTER_CONFIGS:
        logger.warning(f"Unknown source_id: {source_id}, skipping")
        result["error"] = f"Unknown source_id: {source_id}"
        return date_str, result

    config = NEWSLETTER_CONFIGS[source_id]

    try:
        adapter = _get_adapter_for_source(config)
        scrape_result = adapter.scrape_date(date, excluded_urls)

        history_deduplicated_urls: set[str] | None = None
        if config.deduplicate_across_history:
            canonical_urls = [
                util.canonicalize_url(article["url"])
                for article in scrape_result.get("articles", [])
            ]
            history_deduplicated_urls = storage_service.filter_new_urls_for_history_dedup(
                source_id=config.source_id,
                first_seen_date=date_str,
                canonical_urls=canonical_urls,
            )

        for article in scrape_result.get("articles", []):
            canonical_url = util.canonicalize_url(article["url"])
            if history_deduplicated_urls is not None and canonical_url not in history_deduplicated_urls:
                continue
            article["url"] = canonical_url
            result["articles"].append(article)

        result["network_articles"] = len(result["articles"])

    except Exception as error:
        logger.error(
            f"Error processing {config.display_name} for {date_str}: {error}",
            exc_info=True,
        )
        result["error"] = str(error)

    return date_str, result


def merge_source_results_for_date(date_str: str, source_results: list[tuple[str, dict]]) -> dict:
    url_set: set[str] = set()
    all_articles: list[dict] = []

    total_network_articles = _merge_source_results_deterministically(
        source_results, url_set, all_articles
    )

    return {
        "articles": all_articles,
        "network_fetches": total_network_articles,
    }


def _merge_source_results_deterministically(source_results, url_set, all_articles):
    """Merge per-source results in deterministic order, deduplicating articles by URL.

    Mutates url_set and all_articles. Returns the total network-fetched article count
    across sources for stats.
    """
    total_network_articles = 0

    for source_id, result in source_results:
        if result.get("error"):
            logger.warning(f"Skipping {source_id} due to error: {result['error']}")
            continue

        for article in result["articles"]:
            canonical_url = article["url"]
            if canonical_url not in url_set:
                url_set.add(canonical_url)
                all_articles.append(article)

        total_network_articles += result.get("network_articles", 0)

    return total_network_articles


