import logging
from datetime import date as date_type
from datetime import datetime

import requests

import storage_service
import util
from newsletter_scraper import scrape_date_range
from summarizer import (
    DEFAULT_MODEL,
    DEFAULT_TLDR_REASONING_EFFORT,
    _fetch_tldr_prompt,
    normalize_summary_effort,
    tldr_url,
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
                {
                    **article,
                    "tldr": cached_article.get("tldr", article.get("tldr")),
                    "read": cached_article.get("read", article.get("read")),
                    "removed": cached_article.get("removed", article.get("removed")),
                }
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
    today_str = date_type.today().isoformat()

    sources_str = ", ".join(source_ids) if source_ids else "all"
    excluded_count = len(excluded_urls) if excluded_urls else 0
    logger.info(
        f"start start_date={start_date_text} end_date={end_date_text} sources={sources_str} excluded_count={excluded_count}",
    )

    total_network_fetches = 0
    payloads_by_date: dict[str, dict] = {}
    dates_to_write: set[str] = set()

    # Fetch all cached payloads upfront in one query
    all_cached_payloads = storage_service.get_daily_payloads_range(start_date_text, end_date_text)
    cache_map: dict[str, dict] = {payload["date"]: payload for payload in all_cached_payloads}

    # Fast path: all dates cached and none is today
    all_cached_and_not_today = all(
        util.format_date_for_url(d) != today_str and util.format_date_for_url(d) in cache_map
        for d in dates
    )
    if all_cached_and_not_today:
        ordered = [cache_map[util.format_date_for_url(d)] for d in reversed(dates)]
        return {
            "success": True,
            "payloads": ordered,
            "stats": _build_stats_from_payloads(ordered, total_network_fetches),
            "source": "cache",
        }

    for current_date in dates:
        date_str = util.format_date_for_url(current_date)

        if date_str == today_str:
            cached_payload = cache_map.get(date_str)
            cached_urls: set[str] = set()

            if cached_payload:
                for article in cached_payload.get('articles', []):
                    url = article.get('url', '')
                    canonical_url = util.canonicalize_url(url) if url else ''
                    if canonical_url:
                        cached_urls.add(canonical_url)

            combined_excluded = list(set(excluded_urls or []) | cached_urls)
            result = scrape_date_range(current_date, current_date, source_ids, combined_excluded)
            total_network_fetches += result.get('stats', {}).get('network_fetches', 0)

            new_payload = _build_payload_from_scrape(
                date_str,
                result.get('articles', []),
                result.get('issues', []),
            )
            if cached_payload:
                payloads_by_date[date_str] = _merge_payloads(new_payload, cached_payload)
            else:
                payloads_by_date[date_str] = new_payload
            dates_to_write.add(date_str)
        else:
            cached_payload = cache_map.get(date_str)
            if cached_payload:
                payloads_by_date[date_str] = cached_payload
            else:
                result = scrape_date_range(current_date, current_date, source_ids, excluded_urls)
                total_network_fetches += result.get('stats', {}).get('network_fetches', 0)
                payloads_by_date[date_str] = _build_payload_from_scrape(
                    date_str,
                    result.get('articles', []),
                    result.get('issues', []),
                )
                dates_to_write.add(date_str)

    ordered_payloads = [
        payloads_by_date[util.format_date_for_url(current_date)]
        for current_date in reversed(dates)
    ]
    for date_str in dates_to_write:
        storage_service.set_daily_payload(date_str, payloads_by_date[date_str])

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


def fetch_tldr_prompt_template() -> str:
    return _fetch_tldr_prompt()


def tldr_url_content(
    url: str,
    *,
    summary_effort: str = DEFAULT_TLDR_REASONING_EFFORT,
    model: str = DEFAULT_MODEL,
) -> dict:
    cleaned_url = (url or "").strip()
    if not cleaned_url:
        raise ValueError("Missing url")

    canonical_url = util.canonicalize_url(cleaned_url)
    normalized_effort = normalize_summary_effort(summary_effort)

    try:
        tldr_markdown = tldr_url(
            canonical_url,
            summary_effort=normalized_effort,
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
        "tldr_markdown": tldr_markdown,
        "canonical_url": canonical_url,
        "summary_effort": normalized_effort,
    }
