#!/usr/bin/env python3
"""
TLDR Newsletter Scraper Backend with Proxy
"""

from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime
import requests

from blob_store import (
    build_scraped_day_cache_key,
    delete_file,
)
import util
from summarizer import (
    summarize_url,
    _fetch_summarize_prompt,
    summary_blob_pathname,
    normalize_summary_effort,
)
from removed_urls import add_removed_url
import cache_mode
from newsletter_scraper import scrape_date_range

app = Flask(__name__)
logging.basicConfig(level=util.resolve_env_var("LOG_LEVEL", "INFO"))
logger = logging.getLogger("serve")


@app.route("/")
def index():
    """Serve the main page"""
    return render_template("index.html")


@app.route("/api/scrape", methods=["POST"])
def scrape_newsletters():
    """Backend proxy to scrape TLDR newsletters"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data received"}), 400

        # Validate required fields
        if "start_date" not in data or "end_date" not in data:
            return jsonify({
                "success": False,
                "error": "start_date and end_date are required",
            }), 400

        start_date = datetime.fromisoformat(data["start_date"])
        end_date = datetime.fromisoformat(data["end_date"])

        # Backend validation
        if start_date > end_date:
            return jsonify({
                "success": False,
                "error": "start_date must be before or equal to end_date",
            }), 400

        # Limit maximum date range to prevent abuse (31 days inclusive)
        if (end_date - start_date).days >= 31:
            return jsonify({
                "success": False,
                "error": "Date range cannot exceed 31 days",
            }), 400

        util.log(
            f"[serve.scrape_newsletters] start start_date={data['start_date']} end_date={data['end_date']}",
            logger=logger,
        )
        result = scrape_date_range(start_date, end_date)
        util.log(
            f"[serve.scrape_newsletters] done dates_processed={result['stats']['dates_processed']} total_articles={result['stats']['total_articles']}",
            logger=logger,
        )
        return jsonify(result)

    except Exception as e:
        logger.exception(
            "[serve.scrape_newsletters] Failed to scrape newsletters: %s", e
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/prompt", methods=["GET"])
def get_prompt_template():
    """Return the loaded summarize.md prompt (for debugging/inspection)."""
    try:
        prompt = _fetch_summarize_prompt()
        return prompt, 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as e:
        util.log(
            "[serve.get_prompt_template] error loading prompt=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return (
            f"Error loading prompt: {e!r}",
            500,
            {"Content-Type": "text/plain; charset=utf-8"},
        )


@app.route("/api/summarize-url", methods=["POST"])
def summarize_url_endpoint():
    """Summarize a given URL: fetch HTML, convert to Markdown, insert into template, call OpenAI.

    Accepts optional 'cache_only' parameter to only return cached summaries.
    """
    try:
        data = request.get_json() or {}
        url = data.get("url").strip()
        if not url:
            return jsonify({"success": False, "error": "Missing url"}), 400
        url = util.canonicalize_url(url)
        cache_only = data.get("cache_only", False)
        summary_effort = normalize_summary_effort(data.get("summary_effort", "low"))

        summary = summarize_url(
            url, summary_effort=summary_effort, cache_only=cache_only
        )

        # If cache_only and no cached summary, return success=False
        if summary is None:
            return jsonify({
                "success": False,
                "error": "No cached summary available",
            })

        summary_blob_pathname_value = summary_blob_pathname(
            url, summary_effort=summary_effort
        )
        blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
        summary_blob_url = (
            f"{blob_base_url}/{summary_blob_pathname_value}" if blob_base_url else None
        )

        return jsonify({
            "success": True,
            "summary_markdown": summary,
            "summary_blob_url": summary_blob_url,
            "summary_blob_pathname": summary_blob_pathname_value,
        })

    except requests.RequestException as e:
        util.log(
            "[serve.summarize_url_endpoint] request error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": f"Network error: {repr(e)}"}), 502

    except Exception as e:
        util.log(
            "[serve.summarize_url_endpoint] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/remove-url", methods=["POST"])
def remove_url_endpoint():
    """Mark a URL as removed so it won't appear in future scrapes."""
    try:
        data = request.get_json() or {}
        url = (data.get("url") or "").strip()

        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return jsonify({"success": False, "error": "Invalid or missing url"}), 400

        canonical = util.canonicalize_url(url)
        success = add_removed_url(canonical)

        if success:
            return jsonify({"success": True, "canonical_url": canonical})
        else:
            return jsonify({
                "success": False,
                "error": "Failed to persist removal",
            }), 500

    except Exception as e:
        util.log(
            "[serve.remove_url_endpoint] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/cache-mode", methods=["GET"])
def get_cache_mode_endpoint():
    """Get the current cache mode."""
    try:
        mode = cache_mode.get_cache_mode()
        return jsonify({
            "success": True,
            "cache_mode": mode.value,
        })
    except Exception as e:
        util.log(
            "[serve.get_cache_mode_endpoint] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/cache-mode", methods=["POST"])
def set_cache_mode_endpoint():
    """Set the cache mode."""
    try:
        data = request.get_json() or {}
        mode_str = (data.get("cache_mode") or "").strip().lower()

        if not mode_str:
            return jsonify({"success": False, "error": "cache_mode is required"}), 400

        try:
            mode = cache_mode.CacheMode(mode_str)
        except ValueError:
            valid_modes = [m.value for m in cache_mode.CacheMode]
            return jsonify({
                "success": False,
                "error": f"Invalid cache_mode. Valid values: {', '.join(valid_modes)}",
            }), 400

        success = cache_mode.set_cache_mode(mode)

        if success:
            return jsonify({
                "success": True,
                "cache_mode": mode.value,
            })
        else:
            return jsonify({"success": False, "error": "Failed to set cache mode"}), 500

    except Exception as e:
        util.log(
            "[serve.set_cache_mode_endpoint] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/invalidate-cache", methods=["POST"])
def invalidate_cache_endpoint():
    """Invalidate the day-level newsletter cache for a date range.

    This only clears the scraped newsletter cache (scrape-day-*.json files),
    not article content or summaries.
    """
    try:
        data = request.get_json() or {}

        if "start_date" not in data or "end_date" not in data:
            return jsonify({
                "success": False,
                "error": "start_date and end_date are required",
            }), 400

        start_date = datetime.fromisoformat(data["start_date"])
        end_date = datetime.fromisoformat(data["end_date"])

        if start_date > end_date:
            return jsonify({
                "success": False,
                "error": "start_date must be before or equal to end_date",
            }), 400

        dates = util.get_date_range(start_date, end_date)

        # Build list of potential cache entries
        potential_pathnames = []
        for date in dates:
            date_str = util.format_date_for_url(date)
            pathname = build_scraped_day_cache_key(date_str)
            potential_pathnames.append(pathname)

        # Check which entries actually exist
        from blob_store import list_existing_entries
        existing_entries = list_existing_entries(potential_pathnames)
        
        util.log(
            f"[serve.invalidate_cache_endpoint] Found {len(existing_entries)} existing entries out of {len(potential_pathnames)} potential entries",
            logger=logger,
        )

        deleted_count = 0
        failed_count = 0
        errors = []

        for pathname in existing_entries:
            try:
                success = delete_file(pathname)
                if success:
                    deleted_count += 1
                    util.log(
                        f"[serve.invalidate_cache_endpoint] Deleted cache for pathname={pathname}",
                        logger=logger,
                    )
                else:
                    failed_count += 1
                    errors.append(f"{pathname}: delete returned false")
            except Exception as e:
                failed_count += 1
                error_msg = f"{pathname}: {repr(e)}"
                errors.append(error_msg)
                util.log(
                    f"[serve.invalidate_cache_endpoint] Failed to delete cache for pathname={pathname} error={repr(e)}",
                    level=logging.WARNING,
                    logger=logger,
                )

        # Log final summary
        util.log(
            f"[serve.invalidate_cache_endpoint] Completed: {deleted_count} successful deletions, {failed_count} failed deletions out of {len(existing_entries)} existing entries",
            logger=logger,
        )

        overall_success = failed_count == 0
        return jsonify({
            "success": overall_success,
            "deleted": deleted_count,
            "failed": failed_count,
            "total_existing_entries": len(existing_entries),
            "total_potential_entries": len(potential_pathnames),
            "errors": errors if errors else None,
        })

    except Exception as e:
        util.log(
            "[serve.invalidate_cache_endpoint] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/invalidate-date-cache", methods=["POST"])
def invalidate_date_cache_endpoint():
    """Invalidate all cached data (newsletter, URL content, summaries) for a specific date."""
    try:
        data = request.get_json() or {}

        if "date" not in data:
            return jsonify({
                "success": False,
                "error": "date is required",
            }), 400

        date_str = data["date"]

        from blob_store import normalize_url_to_pathname
        from summarizer import SUMMARY_EFFORT_OPTIONS

        deleted_files = []
        failed_files = []

        day_cache_pathname = build_scraped_day_cache_key(date_str)

        blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
        if not blob_base_url:
            return jsonify({
                "success": False,
                "error": "BLOB_STORE_BASE_URL not configured",
            }), 500

        try:
            blob_url = f"{blob_base_url}/{day_cache_pathname}"
            response = requests.get(blob_url, timeout=10)
            response.raise_for_status()
            cached_day = response.json()
            articles = cached_day.get("articles", [])
        except Exception as e:
            util.log(
                f"[serve.invalidate_date_cache_endpoint] Could not fetch day cache for date={date_str}: {repr(e)}",
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
            url_base_pathname = normalize_url_to_pathname(url)
            url_base = (
                url_base_pathname[:-3]
                if url_base_pathname.endswith(".md")
                else url_base_pathname
            )

            content_pathname = url_base_pathname
            if delete_file(content_pathname):
                deleted_files.append(content_pathname)
            else:
                failed_files.append(content_pathname)

            for effort in SUMMARY_EFFORT_OPTIONS:
                suffix = "" if effort == "low" else f"-{effort}"
                summary_pathname = f"{url_base}-summary{suffix}.md"
                if delete_file(summary_pathname):
                    deleted_files.append(summary_pathname)

        if delete_file(day_cache_pathname):
            deleted_files.append(day_cache_pathname)
        else:
            failed_files.append(day_cache_pathname)

        util.log(
            f"[serve.invalidate_date_cache_endpoint] Deleted {len(deleted_files)} files for date={date_str}",
            logger=logger,
        )

        return jsonify({
            "success": True,
            "date": date_str,
            "deleted_count": len(deleted_files),
            "failed_count": len(failed_files),
            "deleted_files": deleted_files[:10],
            "failed_files": failed_files if failed_files else None,
        })

    except Exception as e:
        util.log(
            "[serve.invalidate_date_cache_endpoint] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        threaded=False,
        use_reloader=True,
        use_evalex=True,
        processes=1,
        use_debugger=True,
    )
