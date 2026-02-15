import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date as date_type
from datetime import datetime

import requests

import storage_service
import util
from newsletter_scraper import (
    get_default_source_ids,
    merge_source_results_for_date,
    scrape_single_source_for_date,
)
from summarizer import (
    DEFAULT_MODEL,
    DEFAULT_SUMMARY_EFFORT,
    _fetch_summary_prompt,
    normalize_summarize_effort,
    summarize_url,
)

logger = logging.getLogger("tldr_service")


def _parse_date_range(
    start_date_text: str, end_date_text: str
) -> tuple[datetime, datetime]:
    """Parse ISO date strings and enforce range limits.

    >>> _parse_date_range("2024-01-01", "2024-01-02")[0].isoformat()
    '2024-01-01T00:00:00'
    """
    if not start_date_text or not end_date_text:
        raise ValueError("start_date and end_date are required")

    try:
        start_date = datetime.fromisoformat(start_date_text)
        end_date = datetime.fromisoformat(end_date_text)
    except ValueError as error:
        raise ValueError("Dates must be ISO formatted (YYYY-MM-DD)") from error

    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")

    if (end_date - start_date).days >= 31:
        raise ValueError("Date range cannot exceed 31 days")

    return start_date, end_date


def _build_default_article_state() -> dict:
    return {
        "tldr": {
            "status": "unknown",
            "markdown": "",
            "effort": "low",
            "checkedAt": None,
            "errorMessage": None,
        },
        "read": {"isRead": False, "markedAt": None},
    }


_SERVER_ORIGIN_FIELDS = ("url", "title", "articleMeta", "issueDate", "category", "sourceId", "section", "sectionEmoji", "sectionOrder", "newsletterType")


def _article_to_payload(article: dict) -> dict:
    defaults = _build_default_article_state()
    return {
        "url": article.get("url", ""),
        "title": article.get("title", ""),
        "articleMeta": article.get("article_meta", ""),
        "issueDate": article.get("date", ""),
        "category": article.get("category", ""),
        "sourceId": article.get("source_id"),
        "section": article.get("section_title"),
        "sectionEmoji": article.get("section_emoji"),
        "sectionOrder": article.get("section_order"),
        "newsletterType": article.get("newsletter_type"),
        "removed": bool(article.get("removed", False)),
        "tldr": defaults["tldr"],
        "read": defaults["read"],
    }


def _build_payload_from_scrape(date_str: str, articles: list[dict], issues: list[dict]) -> dict:
    payload_articles = [_article_to_payload(article) for article in articles]
    payload_issues = [issue for issue in issues if issue.get("date") == date_str]
    return {"date": date_str, "articles": payload_articles, "issues": payload_issues}


def _merge_payloads(new_payload: dict, cached_payload: dict) -> dict:
    merged_articles: list[dict] = []
    cached_by_url = {item.get("url"): item for item in cached_payload.get("articles", [])}
    seen_urls = set()

    for article in new_payload.get("articles", []):
        url = article.get("url")
        if url:
            seen_urls.add(url)
        cached_article = cached_by_url.get(url)
        if cached_article:
            merged_articles.append(
                {**cached_article, **{k: article[k] for k in _SERVER_ORIGIN_FIELDS}}
            )
        else:
            merged_articles.append(article)

    for cached_article in cached_payload.get("articles", []):
        url = cached_article.get("url")
        if url and url in seen_urls:
            continue
        merged_articles.append(cached_article)

    merged_issues = cached_payload.get("issues") or new_payload.get("issues") or []
    if cached_payload.get("issues") and new_payload.get("issues"):
        seen_issue_keys = set()
        merged_issues = []
        for issue in cached_payload.get("issues", []) + new_payload.get("issues", []):
            key = (issue.get("date"), issue.get("source_id"), issue.get("category"))
            if key in seen_issue_keys:
                continue
            seen_issue_keys.add(key)
            merged_issues.append(issue)

    return {
        "date": new_payload.get("date"),
        "articles": merged_articles,
        "issues": merged_issues,
    }


def _build_stats_from_payloads(payloads: list[dict], total_network_fetches: int) -> dict:
    unique_urls = set()
    total_articles = 0
    dates_with_content = 0

    for payload in payloads:
        articles = payload.get("articles", [])
        if articles:
            dates_with_content += 1
        for article in articles:
            url = article.get("url")
            if url:
                unique_urls.add(url)
            total_articles += 1

    return {
        "total_articles": total_articles,
        "unique_urls": len(unique_urls),
        "dates_processed": len(payloads),
        "dates_with_content": dates_with_content,
        "network_fetches": total_network_fetches,
        "cache_mode": "read_write",
    }


def scrape_newsletters_in_date_range(
    start_date_text: str, end_date_text: str, source_ids: list[str] | None = None, excluded_urls: list[str] | None = None
) -> dict:
    """Scrape newsletters in date range with server-side cache integration."""
    start_date, end_date = _parse_date_range(start_date_text, end_date_text)
    dates = util.get_date_range(start_date, end_date)
    resolved_source_ids = source_ids or get_default_source_ids()
    source_order = {
        source_id: index for index, source_id in enumerate(resolved_source_ids)
    }

    sources_str = ", ".join(resolved_source_ids) if resolved_source_ids else "all"
    excluded_count = len(excluded_urls) if excluded_urls else 0
    logger.info(
        f"start start_date={start_date_text} end_date={end_date_text} sources={sources_str} excluded_count={excluded_count}",
    )

    total_network_fetches = 0
    payloads_by_date: dict[str, dict] = {}
    dates_to_write: set[str] = set()
    work_items: list[tuple[date_type, str, str, list[str]]] = []

    # Fetch all cached payloads upfront in one query
    all_cached_rows = storage_service.get_daily_payloads_range(start_date_text, end_date_text)
    cache_map: dict[str, dict] = {}
    cached_at_epoch_map: dict[str, float | None] = {}
    for row in all_cached_rows:
        date_key = row['date']
        cache_map[date_key] = row['payload']
        cached_at_iso = row['cached_at']
        if cached_at_iso is None:
            cached_at_epoch_map[date_key] = None
        else:
            cached_at_epoch_map[date_key] = util.parse_cached_at_epoch_seconds(cached_at_iso)

    # Fast path: all dates cached and fresh (no rescrape needed)
    all_cached_and_fresh = all(
        util.format_date_for_url(d) in cache_map
        and not util.should_rescrape(
            util.format_date_for_url(d),
            cached_at_epoch_map.get(util.format_date_for_url(d)),
        )
        for d in dates
    )
    if all_cached_and_fresh:
        ordered = [cache_map[util.format_date_for_url(d)] for d in reversed(dates)]
        return {
            "success": True,
            "payloads": ordered,
            "stats": _build_stats_from_payloads(ordered, total_network_fetches),
            "source": "cache",
        }

    for current_date in dates:
        date_str = util.format_date_for_url(current_date)
        cached_payload = cache_map.get(date_str)
        cached_at_epoch = cached_at_epoch_map.get(date_str)

        if util.should_rescrape(date_str, cached_at_epoch):
            # Rescrape needed: either no cache or cache is stale
            cached_urls: set[str] = set()
            if cached_payload:
                for article in cached_payload.get('articles', []):
                    url = article.get('url', '')
                    canonical_url = util.canonicalize_url(url) if url else ''
                    if canonical_url:
                        cached_urls.add(canonical_url)

            combined_excluded = list(set(excluded_urls or []) | cached_urls)
            dates_to_write.add(date_str)
            for source_id in resolved_source_ids:
                work_items.append((current_date, date_str, source_id, combined_excluded))
        else:
            # Cache is fresh, use it directly
            payloads_by_date[date_str] = cached_payload

    results_by_date: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    if work_items:
        max_workers = int(util.resolve_env_var("MAX_PARALLEL_SCRAPES", default="20"))
        max_workers = max(1, min(max_workers, len(work_items)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(
                    scrape_single_source_for_date, date_value, source_id, excluded
                ): (date_str, source_id)
                for date_value, date_str, source_id, excluded in work_items
            }
            for future in as_completed(future_to_task):
                task_date_str, source_id = future_to_task[future]
                try:
                    date_str, result = future.result()
                except Exception as error:
                    logger.error(
                        "Scrape task failed date=%s source=%s error=%s",
                        task_date_str,
                        source_id,
                        repr(error),
                        exc_info=True,
                    )
                    result = {
                        "articles": [],
                        "issues": [],
                        "network_articles": 0,
                        "error": str(error),
                        "source_id": source_id,
                    }
                    date_str = task_date_str
                results_by_date[date_str].append((source_id, result))

    for current_date in dates:
        date_str = util.format_date_for_url(current_date)
        if date_str not in dates_to_write:
            continue
        cached_payload = cache_map.get(date_str)
        source_results = results_by_date.get(date_str, [])
        source_results.sort(key=lambda item: source_order.get(item[0], len(source_order)))
        merged_result = merge_source_results_for_date(date_str, source_results)
        total_network_fetches += merged_result.get("network_fetches", 0)

        new_payload = _build_payload_from_scrape(
            date_str,
            merged_result.get("articles", []),
            merged_result.get("issues", []),
        )
        if cached_payload:
            payloads_by_date[date_str] = _merge_payloads(new_payload, cached_payload)
        else:
            payloads_by_date[date_str] = new_payload

    ordered_payloads = [
        payloads_by_date[util.format_date_for_url(current_date)]
        for current_date in reversed(dates)
    ]
    for date_str in dates_to_write:
        storage_service.set_daily_payload_from_scrape(date_str, payloads_by_date[date_str])

    logger.info(
        "done dates_processed=%s total_articles=%s",
        len(ordered_payloads),
        sum(len(payload.get("articles", [])) for payload in ordered_payloads),
    )
    return {
        "success": True,
        "payloads": ordered_payloads,
        "stats": _build_stats_from_payloads(ordered_payloads, total_network_fetches),
        "source": "live",
    }


def fetch_summary_prompt_template() -> str:
    return _fetch_summary_prompt()


def summarize_url_content(
    url: str,
    *,
    summarize_effort: str = DEFAULT_SUMMARY_EFFORT,
    model: str = DEFAULT_MODEL,
) -> dict:
    cleaned_url = (url or "").strip()
    if not cleaned_url:
        raise ValueError("Missing url")

    canonical_url = util.canonicalize_url(cleaned_url)
    normalized_effort = normalize_summarize_effort(summarize_effort)

    try:
        summary_markdown = summarize_url(
            canonical_url,
            summarize_effort=normalized_effort,
            model=model,
        )
    except requests.RequestException as error:
        logger.error(
            "request error error=%s",
            repr(error),
            exc_info=True,
        )
        raise

    return {
        "summary_markdown": summary_markdown,
        "canonical_url": canonical_url,
        "summarize_effort": normalized_effort,
    }
