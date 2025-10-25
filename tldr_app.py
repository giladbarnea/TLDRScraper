import logging
from typing import Optional

import tldr_service

logger = logging.getLogger("tldr_app")


def scrape_newsletters(
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
    return tldr_service.scrape_newsletters_in_date_range(
        start_date_text, end_date_text, source_ids=source_ids
    )


def get_summarize_prompt_template() -> str:
    return tldr_service.fetch_summarize_prompt_template()


def get_tldr_prompt_template() -> str:
    return tldr_service.fetch_tldr_prompt_template()


def summarize_url(
    url: str,
    *,
    summary_effort: str = "low",
) -> dict:
    result = tldr_service.summarize_url_content(
        url,
        summary_effort=summary_effort,
    )

    payload: dict[str, Optional[str]] = {
        "success": True,
        "summary_markdown": result["summary_markdown"],
    }

    canonical_url = result.get("canonical_url")
    if canonical_url:
        payload["canonical_url"] = canonical_url

    summary_effort_value = result.get("summary_effort")
    if summary_effort_value:
        payload["summary_effort"] = summary_effort_value

    return payload


def tldr_url(
    url: str,
    *,
    summary_effort: str = "low",
) -> dict:
    result = tldr_service.tldr_url_content(
        url,
        summary_effort=summary_effort,
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


