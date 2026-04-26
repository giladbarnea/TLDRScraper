import logging
from typing import Optional

import tldr_service
from summarizer import DEFAULT_MODEL, DEFAULT_THINKING_EFFORT

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


def generate_digest(articles: list[dict], effort: str = "low") -> dict:
    """Generate a multi-article digest and return the shaped response payload."""
    result = tldr_service.generate_digest(articles, effort)
    return {
        "success": True,
        "digest_id": result["digest_id"],
        "digest_markdown": result["digest_markdown"],
        "article_count": result["article_count"],
        "included_urls": result["included_urls"],
        "skipped": result["skipped"],
    }


def summarize_url(
    url: str,
    *,
    summarize_effort: str = DEFAULT_THINKING_EFFORT,
    model: str = DEFAULT_MODEL,
) -> dict:
    result = tldr_service.summarize_url_content(
        url,
        summarize_effort=summarize_effort,
        model=model,
    )

    payload: dict[str, Optional[str]] = {
        "success": True,
        "summary_markdown": result["summary_markdown"],
    }

    canonical_url = result.get("canonical_url")
    if canonical_url:
        payload["canonical_url"] = canonical_url

    summarize_effort_value = result.get("summarize_effort")
    if summarize_effort_value:
        payload["summarize_effort"] = summarize_effort_value

    return payload


def elaborate(
    selected_text: str,
    source_markdown: str,
    article_urls: list[str],
    *,
    model: str,
) -> dict:
    """Shape the elaboration response for the HTTP layer.

    `article_urls` must be a non-empty list. Returns `canonical_urls` (plural) in the same
    order as the input.
    """
    result = tldr_service.elaborate_content(
        selected_text,
        source_markdown,
        article_urls,
        model=model,
    )

    return {
        "success": True,
        "elaboration_markdown": result["elaboration_markdown"],
        "canonical_urls": result["canonical_urls"],
    }


