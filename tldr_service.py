import logging
from datetime import datetime
from typing import Optional

import requests

import util
from newsletter_scraper import scrape_date_range
from removed_urls import add_removed_url
from summarizer import (
    _fetch_summarize_prompt,
    normalize_summary_effort,
    summarize_url,
    summary_blob_pathname,
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


def scrape_newsletters(start_date_text: str, end_date_text: str) -> dict:
    start_date, end_date = _parse_date_range(start_date_text, end_date_text)
    util.log(
        f"[tldr_service.scrape_newsletters] start start_date={start_date_text} end_date={end_date_text}",
        logger=logger,
    )
    result = scrape_date_range(start_date, end_date)
    util.log(
        f"[tldr_service.scrape_newsletters] done dates_processed={result['stats']['dates_processed']} total_articles={result['stats']['total_articles']}",
        logger=logger,
    )
    return result


def fetch_prompt_template() -> str:
    return _fetch_summarize_prompt()


def summarize_url_content(
    url: str,
    *,
    cache_only: bool = False,
    summary_effort: str = "low",
) -> Optional[dict]:
    cleaned_url = (url or "").strip()
    if not cleaned_url:
        raise ValueError("Missing url")

    canonical_url = util.canonicalize_url(cleaned_url)
    normalized_effort = normalize_summary_effort(summary_effort)

    try:
        summary_markdown = summarize_url(
            canonical_url,
            summary_effort=normalized_effort,
            cache_only=cache_only,
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

    if summary_markdown is None:
        return None

    summary_blob_pathname_value = summary_blob_pathname(
        canonical_url, summary_effort=normalized_effort
    )
    blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
    summary_blob_url = (
        f"{blob_base_url}/{summary_blob_pathname_value}" if blob_base_url else None
    )

    return {
        "summary_markdown": summary_markdown,
        "summary_blob_pathname": summary_blob_pathname_value,
        "summary_blob_url": summary_blob_url,
        "canonical_url": canonical_url,
        "summary_effort": normalized_effort,
    }


def remove_url(url: str) -> str:
    cleaned_url = (url or "").strip()
    if not cleaned_url or not (
        cleaned_url.startswith("http://") or cleaned_url.startswith("https://")
    ):
        raise ValueError("Invalid or missing url")

    canonical_url = util.canonicalize_url(cleaned_url)
    success = add_removed_url(canonical_url)

    if not success:
        raise RuntimeError("Failed to persist removal")

    return canonical_url
