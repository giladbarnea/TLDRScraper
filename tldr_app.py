import logging
from typing import Optional

import tldr_service
from summarizer import DEFAULT_MODEL, DEFAULT_TLDR_REASONING_EFFORT

logger = logging.getLogger("tldr_app")


def scrape_newsletters(
    start_date_text: str, end_date_text: str, source_ids: list[str] | None = None, excluded_urls: list[str] | None = None
) -> dict:
    """Scrape newsletters in date range.

    Args:
        start_date_text: Start date in ISO format
        end_date_text: End date in ISO format
        source_ids: Optional list of source IDs to scrape. Defaults to all configured sources.
        excluded_urls: List of canonical URLs to exclude from results

    Returns:
        Response dictionary with articles and issues
    """
    return tldr_service.scrape_newsletters_in_date_range(
        start_date_text, end_date_text, source_ids=source_ids, excluded_urls=excluded_urls
    )


def tldr_url(
    url: str,
    *,
    summary_effort: str = DEFAULT_TLDR_REASONING_EFFORT,
    model: str = DEFAULT_MODEL,
) -> dict:
    result = tldr_service.tldr_url_content(
        url,
        summary_effort=summary_effort,
        model=model,
    )

    payload: dict[str, Optional[str]] = {
        "success": True,
        "tldr_markdown": result["tldr_markdown"],
    }

    canonical_url = result.get("canonical_url")
    if canonical_url:
        payload["canonical_url"] = canonical_url

    summary_effort_value = result.get("summary_effort")
    if summary_effort_value:
        payload["summary_effort"] = summary_effort_value

    return payload


