import logging
from datetime import datetime

import requests

import util
from newsletter_scraper import scrape_date_range
from summarizer import (
    _fetch_summarize_prompt,
    _fetch_tldr_prompt,
    normalize_summary_effort,
    summarize_url,
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


def scrape_newsletters_in_date_range(
    start_date_text: str, end_date_text: str, source_ids: list[str] | None = None
) -> dict:
    """Scrape newsletters in date range.

    Args:
        start_date_text: Start date in ISO format
        end_date_text: End date in ISO format
        source_ids: Optional list of source IDs to scrape. Defaults to all configured sources.

    Returns:
        Response dictionary with articles and issues
    """
    start_date, end_date = _parse_date_range(start_date_text, end_date_text)

    sources_str = ", ".join(source_ids) if source_ids else "all"
    util.log(
        f"[tldr_service.scrape_newsletters] start start_date={start_date_text} end_date={end_date_text} sources={sources_str}",
        logger=logger,
    )

    result = scrape_date_range(start_date, end_date, source_ids=source_ids)

    util.log(
        f"[tldr_service.scrape_newsletters] done dates_processed={result['stats']['dates_processed']} total_articles={result['stats']['total_articles']}",
        logger=logger,
    )
    return result


def fetch_summarize_prompt_template() -> str:
    return _fetch_summarize_prompt()


def fetch_tldr_prompt_template() -> str:
    return _fetch_tldr_prompt()


def summarize_url_content(
    url: str,
    *,
    summary_effort: str = "low",
) -> dict:
    cleaned_url = (url or "").strip()
    if not cleaned_url:
        raise ValueError("Missing url")

    canonical_url = util.canonicalize_url(cleaned_url)
    normalized_effort = normalize_summary_effort(summary_effort)

    try:
        summary_markdown = summarize_url(
            canonical_url,
            summary_effort=normalized_effort,
        )
    except requests.RequestException as error:
        util.log(
            "[tldr_service.summarize_url_content] request error error=%s",
            repr(error),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        raise

    return {
        "summary_markdown": summary_markdown,
        "canonical_url": canonical_url,
        "summary_effort": normalized_effort,
    }


def tldr_url_content(
    url: str,
    *,
    summary_effort: str = "low",
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
        )
    except requests.RequestException as error:
        util.log(
            "[tldr_service.tldr_url_content] request error error=%s",
            repr(error),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        raise

    return {
        "tldr_markdown": tldr_markdown,
        "canonical_url": canonical_url,
        "summary_effort": normalized_effort,
    }
