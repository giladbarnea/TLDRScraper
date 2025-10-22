import logging
from datetime import datetime
from typing import Optional

import util
import tldr_service

_CACHE_MODE = "read_write"

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


def remove_url(url: str) -> dict:
    canonical_url = tldr_service.remove_url(url)
    return {"success": True, "canonical_url": canonical_url}


def list_removed_urls() -> dict:
    return {"success": True, "removed_urls": []}


def get_cache_mode() -> dict:
    return {"success": True, "cache_mode": _CACHE_MODE}


def set_cache_mode(mode_str: Optional[str]) -> dict:
    _ = (mode_str or "").strip().lower()
    return {"success": True, "cache_mode": _CACHE_MODE}


def invalidate_cache_in_date_range(
    start_date_text: Optional[str], end_date_text: Optional[str]
) -> dict:
    if not start_date_text or not end_date_text:
        raise ValueError("start_date and end_date are required")
    start_date = datetime.fromisoformat(start_date_text)
    end_date = datetime.fromisoformat(end_date_text)

    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")

    dates = util.get_date_range(start_date, end_date)

    util.log(
        f"[tldr_app.invalidate_cache_in_date_range] Stateless backend - nothing to invalidate for {len(dates)} dates",
        logger=logger,
    )

    return {
        "success": True,
        "deleted": 0,
        "failed": 0,
        "total_existing_entries": 0,
        "total_potential_entries": len(dates),
        "errors": None,
    }


def invalidate_cache_for_date(date_text: Optional[str]) -> dict:
    if not date_text:
        raise ValueError("date is required")

    util.log(
        f"[tldr_app.invalidate_cache_for_date] Stateless backend - no cache to clear for {date_text}",
        logger=logger,
    )

    return {
        "success": True,
        "date": date_text,
        "deleted_count": 0,
        "failed_count": 0,
        "deleted_files": [],
        "failed_files": None,
    }
