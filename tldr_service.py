import logging
from datetime import datetime
from typing import Any, Dict, Optional

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


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class ValidationError(ServiceError):
    pass


class ProcessingError(ServiceError):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, status_code=status_code)


def _parse_iso_date(value: Optional[str], field_name: str) -> datetime:
    if not value:
        raise ValidationError(f"{field_name} is required")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO formatted date string"
        ) from exc


def scrape_newsletters(start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    start = _parse_iso_date(start_date, "start_date")
    end = _parse_iso_date(end_date, "end_date")

    if start > end:
        raise ValidationError("start_date must be before or equal to end_date")

    if (end - start).days >= 31:
        raise ValidationError("Date range cannot exceed 31 days")

    util.log(
        f"[tldr_service.scrape_newsletters] start start_date={start_date} end_date={end_date}",
        logger=logger,
    )

    try:
        result = scrape_date_range(start, end)
    except Exception as exc:
        util.log(
            f"[tldr_service.scrape_newsletters] failed error={repr(exc)}",
            level=logging.ERROR,
            logger=logger,
            exc_info=True,
        )
        raise ProcessingError(str(exc)) from exc

    util.log(
        (
            "[tldr_service.scrape_newsletters] done dates_processed="
            f"{result['stats']['dates_processed']} total_articles={result['stats']['total_articles']}"
        ),
        logger=logger,
    )
    return result


def fetch_prompt_template() -> str:
    try:
        return _fetch_summarize_prompt()
    except Exception as exc:
        util.log(
            f"[tldr_service.fetch_prompt_template] failed error={repr(exc)}",
            level=logging.ERROR,
            logger=logger,
            exc_info=True,
        )
        raise ProcessingError(f"Error loading prompt: {exc!r}") from exc


def summarize_url_content(
    url: Optional[str],
    *,
    cache_only: bool = False,
    summary_effort: str = "low",
) -> Dict[str, Any]:
    if not url or not url.strip():
        raise ValidationError("Missing url")

    canonical_url = util.canonicalize_url(url.strip())
    normalized_effort = normalize_summary_effort(summary_effort)

    try:
        summary = summarize_url(
            canonical_url,
            summary_effort=normalized_effort,
            cache_only=cache_only,
        )
    except requests.RequestException as exc:
        util.log(
            f"[tldr_service.summarize_url_content] network error error={repr(exc)}",
            level=logging.ERROR,
            logger=logger,
            exc_info=True,
        )
        raise ProcessingError(f"Network error: {repr(exc)}", status_code=502) from exc
    except Exception as exc:
        util.log(
            f"[tldr_service.summarize_url_content] failed error={repr(exc)}",
            level=logging.ERROR,
            logger=logger,
            exc_info=True,
        )
        raise ProcessingError(repr(exc)) from exc

    if summary is None:
        return {"success": False, "error": "No cached summary available"}

    summary_blob_pathname_value = summary_blob_pathname(
        canonical_url, summary_effort=normalized_effort
    )
    blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
    summary_blob_url = (
        f"{blob_base_url}/{summary_blob_pathname_value}" if blob_base_url else None
    )

    return {
        "success": True,
        "summary_markdown": summary,
        "summary_blob_url": summary_blob_url,
        "summary_blob_pathname": summary_blob_pathname_value,
    }


def remove_url(url: Optional[str]) -> Dict[str, Any]:
    if not url or not url.strip():
        raise ValidationError("Invalid or missing url")

    cleaned = url.strip()
    if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
        raise ValidationError("Invalid or missing url")

    canonical = util.canonicalize_url(cleaned)

    try:
        success = add_removed_url(canonical)
    except Exception as exc:
        util.log(
            f"[tldr_service.remove_url] failed error={repr(exc)}",
            level=logging.ERROR,
            logger=logger,
            exc_info=True,
        )
        raise ProcessingError(repr(exc)) from exc

    if not success:
        raise ProcessingError("Failed to persist removal")

    return {"success": True, "canonical_url": canonical}
