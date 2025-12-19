import logging
from datetime import date as date_type
from datetime import datetime

import requests

import storage_service
import util
from newsletter_scraper import _build_scrape_response, scrape_date_range
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


def _cached_article_to_internal(article: dict) -> dict:
    """Convert cached article (client camelCase format) to internal format (snake_case)."""
    return {
        "url": article.get("url", ""),
        "title": article.get("title", ""),
        "article_meta": article.get("articleMeta", ""),
        "date": article.get("issueDate", ""),
        "category": article.get("category", ""),
        "removed": article.get("removed", False),
        "source_id": article.get("sourceId"),
        "section_title": article.get("section"),
        "section_emoji": article.get("sectionEmoji"),
        "section_order": article.get("sectionOrder"),
        "newsletter_type": article.get("newsletterType"),
    }


def scrape_newsletters_in_date_range(
    start_date_text: str, end_date_text: str, source_ids: list[str] | None = None, excluded_urls: list[str] | None = None
) -> dict:
    """Scrape newsletters in date range with server-side cache integration.

    For past dates: Uses cached data if available, otherwise scrapes.
    For today: Unions cached articles with newly scraped articles (excluding cached URLs).

    Args:
        start_date_text: Start date in ISO format
        end_date_text: End date in ISO format
        source_ids: Optional list of source IDs to scrape. Defaults to all configured sources.
        excluded_urls: List of canonical URLs to exclude from results

    Returns:
        Response dictionary with articles and issues
    """
    start_date, end_date = _parse_date_range(start_date_text, end_date_text)
    dates = util.get_date_range(start_date, end_date)
    today_str = date_type.today().isoformat()

    sources_str = ", ".join(source_ids) if source_ids else "all"
    excluded_count = len(excluded_urls) if excluded_urls else 0
    logger.info(
        f"[tldr_service.scrape_newsletters] start start_date={start_date_text} end_date={end_date_text} sources={sources_str} excluded_count={excluded_count}",
    )

    all_articles: list[dict] = []
    url_set: set[str] = set()
    issue_metadata_by_key: dict[tuple[str, str, str], dict] = {}
    total_network_fetches = 0

    for current_date in dates:
        date_str = util.format_date_for_url(current_date)

        if date_str == today_str:
            # TODAY: Server-Side Union - merge cached + newly scraped
            cached_payload = storage_service.get_daily_payload(date_str)
            cached_urls: set[str] = set()

            if cached_payload:
                for article in cached_payload.get('articles', []):
                    url = article.get('url', '')
                    canonical_url = util.canonicalize_url(url) if url else ''
                    if canonical_url and canonical_url not in url_set:
                        cached_urls.add(canonical_url)
                        url_set.add(canonical_url)
                        all_articles.append(_cached_article_to_internal(article))

                for issue in cached_payload.get('issues', []):
                    key = (issue.get('date'), issue.get('source_id'), issue.get('category'))
                    if key not in issue_metadata_by_key:
                        issue_metadata_by_key[key] = issue

            # Scrape today with cached URLs excluded
            combined_excluded = list(set(excluded_urls or []) | cached_urls)
            result = scrape_date_range(current_date, current_date, source_ids, combined_excluded)
            total_network_fetches += result.get('stats', {}).get('network_fetches', 0)

            # Add newly scraped articles
            for article in result.get('articles', []):
                url = article.get('url', '')
                canonical_url = util.canonicalize_url(url) if url else ''
                if canonical_url and canonical_url not in url_set:
                    url_set.add(canonical_url)
                    all_articles.append(article)

            for issue in result.get('issues', []):
                key = (issue.get('date'), issue.get('source_id'), issue.get('category'))
                if key not in issue_metadata_by_key:
                    issue_metadata_by_key[key] = issue
        else:
            # PAST DATE: Cache-first
            cached_payload = storage_service.get_daily_payload(date_str)
            if cached_payload:
                for article in cached_payload.get('articles', []):
                    url = article.get('url', '')
                    canonical_url = util.canonicalize_url(url) if url else ''
                    if canonical_url and canonical_url not in url_set:
                        url_set.add(canonical_url)
                        all_articles.append(_cached_article_to_internal(article))

                for issue in cached_payload.get('issues', []):
                    key = (issue.get('date'), issue.get('source_id'), issue.get('category'))
                    if key not in issue_metadata_by_key:
                        issue_metadata_by_key[key] = issue
            else:
                # Not cached, must scrape
                result = scrape_date_range(current_date, current_date, source_ids, excluded_urls)
                total_network_fetches += result.get('stats', {}).get('network_fetches', 0)

                for article in result.get('articles', []):
                    url = article.get('url', '')
                    canonical_url = util.canonicalize_url(url) if url else ''
                    if canonical_url and canonical_url not in url_set:
                        url_set.add(canonical_url)
                        all_articles.append(article)

                for issue in result.get('issues', []):
                    key = (issue.get('date'), issue.get('source_id'), issue.get('category'))
                    if key not in issue_metadata_by_key:
                        issue_metadata_by_key[key] = issue

    # Ensure all articles have removed field
    for article in all_articles:
        article.setdefault("removed", False)

    result = _build_scrape_response(
        start_date,
        end_date,
        dates,
        all_articles,
        url_set,
        issue_metadata_by_key,
        total_network_fetches,
    )

    logger.info(
        f"[tldr_service.scrape_newsletters] done dates_processed={result['stats']['dates_processed']} total_articles={result['stats']['total_articles']}",
    )
    return result


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
            "[tldr_service.tldr_url_content] request error error=%s",
            repr(error),
            exc_info=True,
        )
        raise

    return {
        "tldr_markdown": tldr_markdown,
        "canonical_url": canonical_url,
        "summary_effort": normalized_effort,
    }
