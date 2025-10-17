import logging
from datetime import datetime
from typing import Optional

import requests

import blob_store
import cache_mode
import util
import tldr_service
from removed_urls import get_removed_urls as _get_removed_urls
from summarizer import (
    summary_blob_pathname,
    summary_legacy_blob_pathnames,
)

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
    cache_only: bool = False,
    summary_effort: str = "low",
) -> dict:
    result = tldr_service.summarize_url_content(
        url,
        cache_only=cache_only,
        summary_effort=summary_effort,
    )

    if result is None:
        return {"success": False, "error": "No cached summary available"}

    payload: dict[str, Optional[str]] = {
        "success": True,
        "summary_markdown": result["summary_markdown"],
        "summary_blob_url": result["summary_blob_url"],
        "summary_blob_pathname": result["summary_blob_pathname"],
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
    cache_only: bool = False,
    summary_effort: str = "low",
) -> dict:
    result = tldr_service.tldr_url_content(
        url,
        cache_only=cache_only,
        summary_effort=summary_effort,
    )

    if result is None:
        return {"success": False, "error": "No cached TLDR available"}

    payload: dict[str, Optional[str]] = {
        "success": True,
        "tldr_markdown": result["tldr_markdown"],
        "tldr_blob_url": result["tldr_blob_url"],
        "tldr_blob_pathname": result["tldr_blob_pathname"],
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
    return {"success": True, "removed_urls": list(_get_removed_urls())}


def get_cache_mode() -> dict:
    mode = cache_mode.get_cache_mode()
    return {"success": True, "cache_mode": mode.value}


def set_cache_mode(mode_str: Optional[str]) -> dict:
    normalized_mode = (mode_str or "").strip().lower()
    if not normalized_mode:
        raise ValueError("cache_mode is required")

    try:
        mode = cache_mode.CacheMode(normalized_mode)
    except ValueError as error:
        valid_modes = ", ".join(sorted(m.value for m in cache_mode.CacheMode))
        raise ValueError(
            f"Invalid cache_mode. Valid values: {valid_modes}"
        ) from error

    success = cache_mode.set_cache_mode(mode)
    if not success:
        raise RuntimeError("Failed to set cache mode")

    return {"success": True, "cache_mode": mode.value}


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

    potential_pathnames = []
    for date in dates:
        date_str = util.format_date_for_url(date)
        pathname = blob_store.build_scraped_day_cache_key(date_str)
        potential_pathnames.append(pathname)

    existing_entries = blob_store.list_existing_entries(potential_pathnames)

    util.log(
        f"[tldr_app.invalidate_cache_in_date_range] Found {len(existing_entries)} existing entries out of {len(potential_pathnames)} potential entries",
        logger=logger,
    )

    deleted_count = 0
    failed_count = 0
    errors: list[str] = []

    for pathname in existing_entries:
        try:
            success = blob_store.delete_file(pathname)
            if success:
                deleted_count += 1
                util.log(
                    f"[tldr_app.invalidate_cache_in_date_range] Deleted cache for pathname={pathname}",
                    logger=logger,
                )
            else:
                failed_count += 1
                errors.append(f"{pathname}: delete returned false")
        except Exception as error:
            failed_count += 1
            error_message = f"{pathname}: {repr(error)}"
            errors.append(error_message)
            util.log(
                f"[tldr_app.invalidate_cache_in_date_range] Failed to delete cache for pathname={pathname} error={repr(error)}",
                level=logging.WARNING,
                logger=logger,
            )

    util.log(
        f"[tldr_app.invalidate_cache_in_date_range] Completed: {deleted_count} successful deletions, {failed_count} failed deletions out of {len(existing_entries)} existing entries",
        logger=logger,
    )

    return {
        "success": failed_count == 0,
        "deleted": deleted_count,
        "failed": failed_count,
        "total_existing_entries": len(existing_entries),
        "total_potential_entries": len(potential_pathnames),
        "errors": errors or None,
    }


def invalidate_cache_for_date(date_text: Optional[str]) -> dict:
    if not date_text:
        raise ValueError("date is required")

    deleted_files: list[str] = []
    failed_files: list[str] = []

    day_cache_pathname = blob_store.build_scraped_day_cache_key(date_text)

    blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
    if not blob_base_url:
        raise RuntimeError("BLOB_STORE_BASE_URL not configured")

    try:
        blob_url = f"{blob_base_url}/{day_cache_pathname}"
        response = requests.get(
            blob_url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        response.raise_for_status()
        cached_day = response.json()
        articles = cached_day.get("articles", [])
    except Exception as error:
        util.log(
            f"[tldr_app.invalidate_cache_for_date] Could not fetch day cache for date={date_text}: {repr(error)}",
            level=logging.WARNING,
            logger=logger,
        )
        articles = []

    urls_to_process = set()
    for article in articles:
        url = article.get("url")
        if url:
            canonical = util.canonicalize_url(url)
            urls_to_process.add(canonical)

    for url in urls_to_process:
        content_pathname = blob_store.normalize_url_to_pathname(url)
        if blob_store.delete_file(content_pathname):
            deleted_files.append(content_pathname)
        else:
            failed_files.append(content_pathname)

        summary_candidates = [
            summary_blob_pathname(url),
            *summary_legacy_blob_pathnames(url),
        ]
        seen_summary: set[str] = set()
        for summary_pathname in summary_candidates:
            if summary_pathname in seen_summary:
                continue
            seen_summary.add(summary_pathname)
            if blob_store.delete_file(summary_pathname):
                deleted_files.append(summary_pathname)

    if blob_store.delete_file(day_cache_pathname):
        deleted_files.append(day_cache_pathname)
    else:
        failed_files.append(day_cache_pathname)

    util.log(
        f"[tldr_app.invalidate_cache_for_date] Deleted {len(deleted_files)} files for date={date_text}",
        logger=logger,
    )

    return {
        "success": True,
        "date": date_text,
        "deleted_count": len(deleted_files),
        "failed_count": len(failed_files),
        "deleted_files": deleted_files[:10],
        "failed_files": failed_files or None,
    }
