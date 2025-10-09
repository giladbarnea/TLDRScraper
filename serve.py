#!/usr/bin/env python3
"""
TLDR Newsletter Scraper backend with a proxy.
Important: cli.py must expose the exact same interfaces to the app logic that serve.py exposes via the web. Any changes made here must also be mirrored in cli.py and verified through cli.py.
"""

from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime
import requests

import blob_store
import cache_mode
import util
import tldr_service
import removed_urls

app = Flask(__name__)
logging.basicConfig(level=util.resolve_env_var("LOG_LEVEL", "INFO"))
logger = logging.getLogger("serve")


@app.route("/")
def index():
    """Serve the main page"""
    return render_template("index.html")


@app.route("/api/scrape", methods=["POST"])
def scrape_newsletters_in_date_range():
    """Backend proxy to scrape TLDR newsletters. Expects start_date and end_date in the request body."""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "error": "No JSON data received"}), 400

        result = tldr_service.scrape_newsletters_in_date_range(
            data.get("start_date"),
            data.get("end_date"),
        )
        return jsonify(result)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except Exception as error:
        logger.exception(
            "[serve.scrape_newsletters_in_date_range] Failed to scrape newsletters: %s",
            error,
        )
        return jsonify({"success": False, "error": str(error)}), 500


@app.route("/api/prompt", methods=["GET"])
def get_summarize_prompt_template():
    """Return the loaded summarize.md prompt (for debugging/inspection)."""
    try:
        prompt = tldr_service.fetch_summarize_prompt_template()
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
def summarize_url():
    """Summarize the content at a URL: fetch the HTML, convert it to Markdown, insert it into a template, then call OpenAI.

    Requires 'url'. Optional: 'cache_only' to return only cached summaries, and 'summary_effort' to set the reasoning effort level.
    """
    try:
        data = request.get_json() or {}
        result = tldr_service.summarize_url_content(
            data.get("url", ""),
            cache_only=data.get("cache_only", False),
            summary_effort=data.get("summary_effort", "low"),
        )

        if result is None:
            return jsonify({
                "success": False,
                "error": "No cached summary available",
            })

        response_payload = {
            "success": True,
            "summary_markdown": result["summary_markdown"],
            "summary_blob_url": result["summary_blob_url"],
            "summary_blob_pathname": result["summary_blob_pathname"],
        }

        canonical_url = result.get("canonical_url")
        if canonical_url:
            response_payload["canonical_url"] = canonical_url

        summary_effort = result.get("summary_effort")
        if summary_effort:
            response_payload["summary_effort"] = summary_effort

        return jsonify(response_payload)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except requests.RequestException as e:
        util.log(
            "[serve.summarize_url] request error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": f"Network error: {repr(e)}"}), 502

    except Exception as e:
        util.log(
            "[serve.summarize_url] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/tldr-url", methods=["POST"])
def tldr_url():
    """Create a TLDR of the content at a URL.

    Requires 'url'. Optional: 'cache_only' to return only cached TLDRs, and 'summary_effort' to set the reasoning effort level.
    """
    try:
        data = request.get_json() or {}
        result = tldr_service.tldr_url_content(
            data.get("url", ""),
            cache_only=data.get("cache_only", False),
            summary_effort=data.get("summary_effort", "low"),
        )

        if result is None:
            return jsonify({
                "success": False,
                "error": "No cached TLDR available",
            })

        response_payload = {
            "success": True,
            "tldr_markdown": result["tldr_markdown"],
            "tldr_blob_url": result["tldr_blob_url"],
            "tldr_blob_pathname": result["tldr_blob_pathname"],
        }

        canonical_url = result.get("canonical_url")
        if canonical_url:
            response_payload["canonical_url"] = canonical_url

        summary_effort = result.get("summary_effort")
        if summary_effort:
            response_payload["summary_effort"] = summary_effort

        return jsonify(response_payload)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except requests.RequestException as e:
        util.log(
            "[serve.tldr_url] request error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": f"Network error: {repr(e)}"}), 502

    except Exception as e:
        util.log(
            "[serve.tldr_url] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/remove-url", methods=["POST"])
def remove_url():
    """Mark a URL as removed so it won't appear in future scrapes. Expects 'url' in the request body."""
    try:
        url = request.get_json()["url"]
        assert url, "url is required"
        canonical = tldr_service.remove_url(url)
        return jsonify({"success": True, "canonical_url": canonical})

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"success": False, "error": str(error)}), 500
    except Exception as e:
        util.log(
            "[serve.remove_url] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/removed-urls", methods=["GET"])
def get_removed_urls():
    """Get the list of removed URLs."""
    try:
        return jsonify({
            "success": True,
            "removed_urls": list(removed_urls.get_removed_urls()),
        })
    except Exception as e:
        util.log(
            "[serve.get_removed_urls] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/cache-mode", methods=["GET"])
def get_cache_mode():
    """Get the current cache mode."""
    try:
        mode = cache_mode.get_cache_mode()
        return jsonify({
            "success": True,
            "cache_mode": mode.value,
        })
    except Exception as e:
        util.log(
            "[serve.get_cache_mode] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/cache-mode", methods=["POST"])
def set_cache_mode():
    """Set the cache mode. Expects 'cache_mode' in the request body."""
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
            "[serve.set_cache_mode] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/invalidate-cache", methods=["POST"])
def invalidate_cache_in_date_range():
    """Invalidate the day-level newsletter cache for a date range.

    This only clears the scraped newsletter cache (scrape-day-*.json files),
    not article content or summaries.
    Expects start_date and end_date in the request body.
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
            pathname = blob_store.build_scraped_day_cache_key(date_str)
            potential_pathnames.append(pathname)

        # Check which entries actually exist

        existing_entries = blob_store.list_existing_entries(potential_pathnames)

        util.log(
            f"[serve.invalidate_cache_in_date_range] Found {len(existing_entries)} existing entries out of {len(potential_pathnames)} potential entries",
            logger=logger,
        )

        deleted_count = 0
        failed_count = 0
        errors = []

        for pathname in existing_entries:
            try:
                success = blob_store.delete_file(pathname)
                if success:
                    deleted_count += 1
                    util.log(
                        f"[serve.invalidate_cache_in_date_range] Deleted cache for pathname={pathname}",
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
                    f"[serve.invalidate_cache_in_date_range] Failed to delete cache for pathname={pathname} error={repr(e)}",
                    level=logging.WARNING,
                    logger=logger,
                )

        # Log final summary
        util.log(
            f"[serve.invalidate_cache_in_date_range] Completed: {deleted_count} successful deletions, {failed_count} failed deletions out of {len(existing_entries)} existing entries",
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
            "[serve.invalidate_cache_in_date_range] error error=%s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/invalidate-date-cache", methods=["POST"])
def invalidate_cache_for_date():
    """Invalidate all cached data (newsletter, URL content, summaries) for a specific date.
    Expects date in the request body.
    """
    try:
        data = request.get_json() or {}
        if not data.get("date"):
            return jsonify({
                "success": False,
                "error": "date is required",
            }), 400

        date_str = data["date"]

        from summarizer import SUMMARY_EFFORT_OPTIONS

        deleted_files = []
        failed_files = []

        day_cache_pathname = blob_store.build_scraped_day_cache_key(date_str)

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
                f"[serve.invalidate_cache_for_date] Could not fetch day cache for date={date_str}: {repr(e)}",
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
            url_base_pathname = blob_store.normalize_url_to_pathname(url)
            url_base = (
                url_base_pathname[:-3]
                if url_base_pathname.endswith(".md")
                else url_base_pathname
            )

            content_pathname = url_base_pathname
            if blob_store.delete_file(content_pathname):
                deleted_files.append(content_pathname)
            else:
                failed_files.append(content_pathname)

            for effort in SUMMARY_EFFORT_OPTIONS:
                suffix = "" if effort == "low" else f"-{effort}"
                summary_pathname = f"{url_base}-summary{suffix}.md"
                if blob_store.delete_file(summary_pathname):
                    deleted_files.append(summary_pathname)

        if blob_store.delete_file(day_cache_pathname):
            deleted_files.append(day_cache_pathname)
        else:
            failed_files.append(day_cache_pathname)

        util.log(
            f"[serve.invalidate_cache_for_date] Deleted {len(deleted_files)} files for date={date_str}",
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
            "[serve.invalidate_cache_for_date] error error=%s",
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
