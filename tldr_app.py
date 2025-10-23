import logging
from typing import Optional

import tldr_service

logger = logging.getLogger("tldr_app")


def scrape_newsletters(start_date_text: str, end_date_text: str) -> dict:
    return tldr_service.scrape_newsletters_in_date_range(
        start_date_text, end_date_text
    )


def get_summarize_prompt_template() -> str:
    return tldr_service.fetch_summarize_prompt_template()


def get_tldr_prompt_template() -> str:
    return tldr_service.fetch_tldr_prompt_template()


def summarize_url(
    url: str,
    *,
    summary_effort: str = "low",
    cache_only: bool = False,
) -> dict:
    try:
        result = tldr_service.summarize_url_content(
            url,
            summary_effort=summary_effort,
            cache_only=cache_only,
        )
    except tldr_service.CacheMissError as error:
        return {"success": False, "error": str(error)}

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
    cache_only: bool = False,
) -> dict:
    try:
        result = tldr_service.tldr_url_content(
            url,
            summary_effort=summary_effort,
            cache_only=cache_only,
        )
    except tldr_service.CacheMissError as error:
        return {"success": False, "error": str(error)}

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


