#!/usr/bin/env python3
"""
TLDR Newsletter Scraper backend with a proxy.
"""

import datetime
import importlib
import logging
import os
import pathlib
import sys

from flask import Flask, Response, request, jsonify, send_from_directory
import requests

import podcast_service
import util
import tldr_app
import storage_service

from summarizer import DEFAULT_MODEL, DEFAULT_THINKING_EFFORT, DEFAULT_ELABORATE_MODEL
from source_routes import source_bp

# Configure Flask to serve React build output
app = Flask(
    __name__,
    static_folder='static/dist/assets',
    static_url_path='/assets'
)
app.register_blueprint(source_bp)

# Configure logging with timestamps and detailed format
log_format = "%(asctime)s %(levelname)s │ %(name)s %(filename)s:%(lineno)d %(funcName)s │ %(message)s"
logging.basicConfig(
    level=util.resolve_env_var("LOG_LEVEL", "INFO"),
    format=log_format,
    force=True  # Override any existing configuration
)
logger = logging.getLogger("serve")

def summarize_article_patch(patch: dict) -> str:
    """Return a compact, log-friendly summary of an article patch."""
    patch_keys = ",".join(sorted(patch))
    parts = [f"keys={patch_keys}"]

    removed = patch.get("removed")
    if isinstance(removed, bool):
        parts.append(f"removed={removed}")

    read_patch = patch.get("read")
    if isinstance(read_patch, dict) and "isRead" in read_patch:
        parts.append(f"read={read_patch['isRead']}")

    for summary_field in ("summary", "tldr"):
        summary_patch = patch.get(summary_field)
        if isinstance(summary_patch, dict):
            if "status" in summary_patch:
                parts.append(f"{summary_field}_status={summary_patch['status']}")
            if "effort" in summary_patch:
                parts.append(f"{summary_field}_effort={summary_patch['effort']}")

    return " ".join(parts)


def summarize_daily_payload_patch(patch: dict) -> str:
    """Return a compact, log-friendly summary of a daily payload patch."""
    patch_keys = ",".join(sorted(patch))
    parts = [f"keys={patch_keys}"]

    digest_patch = patch.get("digest")
    if isinstance(digest_patch, dict):
        if "status" in digest_patch:
            parts.append(f"digest_status={digest_patch['status']}")
        if isinstance(digest_patch.get("articleUrls"), list):
            parts.append(f"digest_article_count={len(digest_patch['articleUrls'])}")

    return " ".join(parts)


def persist_article_summary(date: str, url: str, summary_data: dict, max_retries: int = 5) -> dict:
    """Persist a summary into the daily_cache article entry, retrying on optimistic-concurrency conflicts.

    Returns the full updated payload row from `patch_daily_article`. Raises on missing row or retry exhaustion.
    """
    last_conflict_updated_at = None
    for attempt_index in range(max_retries):
        row = storage_service.get_daily_payload_row(date)
        if row is None:
            raise ValueError(f"Daily payload not found for date: {date}")

        rpc_result = storage_service.patch_daily_article(
            date,
            url,
            {"summary": summary_data},
            row["updated_at"],
        )

        if not rpc_result.get("conflict"):
            return {
                "payload": rpc_result.get("payload"),
                "updated_at": rpc_result.get("updated_at"),
            }

        last_conflict_updated_at = rpc_result.get("updated_at")
        logger.info(
            "persist_article_summary conflict date=%s url=%s attempt=%s updated_at=%s",
            date,
            url,
            attempt_index + 1,
            last_conflict_updated_at,
        )

    raise RuntimeError(
        f"persist_article_summary conflict retry exhausted (date={date}, url={url}, attempts={max_retries})"
    )



@app.route("/")
def index():
    """Serve the React app"""
    static_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'dist')
    return send_from_directory(static_dist, 'index.html')



@app.route("/api/scrape", methods=["POST"])
def scrape_newsletters_in_date_range():
    """Backend proxy to scrape newsletters. Expects start_date, end_date, excluded_urls, and optionally sources in the request body."""
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"success": False, "error": "No JSON data received"}), 400

        # Extract sources parameter (optional)
        sources = data.get("sources")
        if sources is not None and not isinstance(sources, list):
            return (
                jsonify(
                    {"success": False, "error": "sources must be an array of source IDs"}
                ),
                400,
            )

        result = tldr_app.scrape_newsletters(
            data.get("start_date"),
            data.get("end_date"),
            source_ids=sources,
            excluded_urls=data.get("excluded_urls", []),
        )
        return jsonify(result)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except Exception as error:
        logger.exception(
            "Failed to scrape newsletters: %s",
            error,
        )
        return jsonify({"success": False, "error": str(error)}), 500

@app.route("/api/summarize-url", methods=["POST"])
def summarize_url_endpoint(model: str = DEFAULT_MODEL):
    """Create a summary of the content at a URL.

    Requires 'url'. Optional: 'issue_date' (YYYY-MM-DD) to persist the summary into Supabase
    for that day's article. 'summarize_effort' to set the reasoning effort level. 'model'
    query param to specify Gemini model.
    """
    try:
        data = request.get_json() or {}
        model_param = request.args.get("model", DEFAULT_MODEL)
        url = data.get("url", "")
        issue_date = data.get("issue_date")
        summarize_effort = data.get("summarize_effort", DEFAULT_THINKING_EFFORT)
        logger.info(
            "summarize_url start url=%s issue_date=%s summarize_effort=%s model=%s",
            url,
            issue_date,
            summarize_effort,
            model_param,
        )
        result = tldr_app.summarize_url(
            url,
            summarize_effort=summarize_effort,
            model=model_param,
        )

        if result.get("success") and issue_date:
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            summary_data = {
                "status": "available",
                "markdown": result["summary_markdown"],
                "effort": summarize_effort,
                "checkedAt": now_iso,
                "errorMessage": None,
            }
            persisted = persist_article_summary(issue_date, url, summary_data)
            result["payload"] = persisted["payload"]
            logger.info(
                "summarize_url persisted url=%s issue_date=%s updated_at=%s",
                url,
                issue_date,
                persisted["updated_at"],
            )

        logger.info(
            "summarize_url done url=%s success=%s persisted=%s",
            url,
            result.get("success"),
            "payload" in result,
        )

        return jsonify(result)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except requests.RequestException as e:
        logger.error(
            "request error error=%s",
            repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": f"Network error: {repr(e)}"}), 502

    except Exception as e:
        logger.error(
            "error error=%s",
            repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/elaborate", methods=["POST"])
def elaborate_endpoint(model: str = DEFAULT_ELABORATE_MODEL):
    """Elaborate on a selected portion of a previously-rendered source (summary or digest).

    Requires 'selected_text' (non-empty string), 'source_markdown' (non-empty string), and
    'article_urls' (non-empty list of strings) in the JSON body. The backend canonicalizes
    each URL, scrapes all of them in parallel, and feeds the concatenated bodies to the
    LLM as <source-articles>. Optional 'model' query param.
    """
    try:
        data = request.get_json()
        model_param = request.args.get("model", DEFAULT_ELABORATE_MODEL)
        result = tldr_app.elaborate(
            data.get("selected_text"),
            data.get("source_markdown"),
            data.get("article_urls"),
            model=model_param,
        )
        return jsonify(result)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except requests.RequestException as error:
        logger.error(
            "request error error=%s",
            repr(error),
            exc_info=True,
        )
        return jsonify({"success": False, "error": f"Network error: {repr(error)}"}), 502
    except Exception as error:
        logger.error(
            "error error=%s",
            repr(error),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(error)}), 500


@app.route("/api/digest", methods=["POST"])
def digest_endpoint():
    """Generate a synthesized digest from multiple article URLs.

    Requires 'articles' list in request body (each with url, title, category).
    Optional: 'effort' to set the reasoning effort level.
    """
    try:
        data = request.get_json()
        result = tldr_app.generate_digest(
            data["articles"],
            effort=data.get("effort", "low"),
        )
        return jsonify(result)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except requests.RequestException as error:
        logger.error(
            "request error error=%s",
            repr(error),
            exc_info=True,
        )
        return jsonify({"success": False, "error": f"Network error: {repr(error)}"}), 502
    except Exception as error:
        logger.error(
            "error error=%s",
            repr(error),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(error)}), 500


@app.route("/api/podcast", methods=["POST"])
def podcast_endpoint():
    """Return an MP3 podcast synthesized from the selected source URLs.

    Requires 'urls' in the request body as a non-empty array of URL strings.
    Response is raw audio/mpeg.
    """
    try:
        data = request.get_json()
        result = podcast_service.get_or_create_podcast_episode(data["urls"])
        response = Response(result["audio_bytes"], mimetype="audio/mpeg")
        response.headers["X-Canonical-Urls"] = ",".join(result["canonical_urls"])
        response.headers["X-Cache"] = "hit" if result["cached"] else "miss"
        return response
    except KeyError as error:
        return jsonify({"success": False, "error": f"Missing field: {error}"}), 400
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except requests.RequestException as error:
        logger.error(
            "request error error=%s",
            repr(error),
            exc_info=True,
        )
        return jsonify({"success": False, "error": f"Network error: {repr(error)}"}), 502
    except Exception as error:
        logger.exception("podcast_endpoint failed: %s", error)
        return jsonify({"success": False, "error": repr(error)}), 500


@app.route("/api/storage/setting/<key>", methods=["GET"])
def get_storage_setting(key):
    """Get setting value by key."""
    try:
        value = storage_service.get_setting(key)
        if value is None:
            return jsonify({"success": False, "error": "Setting not found"}), 404

        return jsonify({"success": True, "value": value})

    except Exception as e:
        logger.error(
            "error key=%s error=%s",
            key, repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500

@app.route("/api/storage/setting/<key>", methods=["POST"])
def set_storage_setting(key):
    """Set setting value by key."""
    try:
        data = request.get_json()
        value = data['value']

        result = storage_service.set_setting(key, value)
        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(
            "error key=%s error=%s",
            key, repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500

@app.route("/api/storage/daily/<date>", methods=["GET"])
def get_storage_daily(date):
    """Get cached payload for a specific date."""
    try:
        row = storage_service.get_daily_payload_row(date)
        if row is None:
            return jsonify({"success": False, "error": "Date not found"}), 404

        return jsonify({
            "success": True,
            "payload": row["payload"],
            "updated_at": row["updated_at"],
        })

    except Exception as e:
        logger.error(
            "error date=%s error=%s",
            date, repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/storage/daily/<date>", methods=["PATCH"])
def patch_storage_daily(date):
    """Patch top-level fields within a daily payload with optimistic concurrency."""
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Invalid JSON body"}), 400

        for key in ['patch', 'expected_updated_at']:
            if key not in data:
                return jsonify({"success": False, "error": f"Missing required field: {key}"}), 400

        if not isinstance(data['patch'], dict):
            return jsonify({"success": False, "error": "Field 'patch' must be an object"}), 400

        if not data['patch']:
            return jsonify({"success": False, "error": "Field 'patch' must not be empty"}), 400

        patch_summary = summarize_daily_payload_patch(data['patch'])
        logger.info(
            "patch_daily_payload start date=%s %s expected_updated_at=%s",
            date,
            patch_summary,
            data['expected_updated_at'],
        )

        rpc_result = storage_service.patch_daily_payload(
            date,
            data['patch'],
            data['expected_updated_at'],
        )

        if rpc_result.get('conflict'):
            logger.info(
                "patch_daily_payload conflict date=%s %s updated_at=%s",
                date,
                patch_summary,
                rpc_result.get('updated_at'),
            )
            return jsonify({
                "success": False,
                "conflict": True,
                "payload": rpc_result.get('payload'),
                "updated_at": rpc_result.get('updated_at'),
            }), 409

        logger.info(
            "patch_daily_payload done date=%s %s updated_at=%s",
            date,
            patch_summary,
            rpc_result.get('updated_at'),
        )
        return jsonify({
            "success": True,
            "payload": rpc_result.get('payload'),
            "updated_at": rpc_result.get('updated_at'),
        })

    except Exception as e:
        logger.error(
            "error date=%s error=%s",
            date, repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/storage/daily/<date>/article", methods=["PATCH"])
def patch_storage_daily_article(date):
    """Patch a single article within a daily payload with optimistic concurrency."""
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Invalid JSON body"}), 400

        for key in ['url', 'patch', 'expected_updated_at']:
            if key not in data:
                return jsonify({"success": False, "error": f"Missing required field: {key}"}), 400

        if not isinstance(data['patch'], dict):
            return jsonify({"success": False, "error": "Field 'patch' must be an object"}), 400

        if not data['patch']:
            return jsonify({"success": False, "error": "Field 'patch' must not be empty"}), 400

        patch_summary = summarize_article_patch(data['patch'])
        logger.info(
            "patch_daily_article start date=%s url=%s %s expected_updated_at=%s",
            date,
            data['url'],
            patch_summary,
            data['expected_updated_at'],
        )

        rpc_result = storage_service.patch_daily_article(
            date,
            data['url'],
            data['patch'],
            data['expected_updated_at'],
        )

        if rpc_result.get('conflict'):
            logger.info(
                "patch_daily_article conflict date=%s url=%s %s updated_at=%s",
                date,
                data['url'],
                patch_summary,
                rpc_result.get('updated_at'),
            )
            return jsonify({
                "success": False,
                "conflict": True,
                "payload": rpc_result.get('payload'),
                "updated_at": rpc_result.get('updated_at'),
            }), 409

        logger.info(
            "patch_daily_article done date=%s url=%s %s updated_at=%s",
            date,
            data['url'],
            patch_summary,
            rpc_result.get('updated_at'),
        )
        return jsonify({
            "success": True,
            "payload": rpc_result.get('payload'),
            "updated_at": rpc_result.get('updated_at'),
        })

    except Exception as e:
        logger.error(
            "error date=%s error=%s",
            date, repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/storage/daily/<date>", methods=["POST"])
def set_storage_daily(date):
    """Save or update daily payload."""
    try:
        data = request.get_json()
        payload = data['payload']

        result = storage_service.set_daily_payload(date, payload)
        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(
            "error date=%s error=%s",
            date, repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500

@app.route("/api/storage/daily-range", methods=["POST"])
def get_storage_daily_range():
    """Get all cached payloads in date range."""
    try:
        data = request.get_json()
        start_date = data['start_date']
        end_date = data['end_date']

        rows = storage_service.get_daily_payloads_range(start_date, end_date)
        payloads = [row['payload'] for row in rows]
        return jsonify({"success": True, "payloads": payloads})

    except Exception as e:
        logger.error(
            "error error=%s",
            repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500

@app.route("/api/storage/is-cached/<date>", methods=["GET"])
def check_storage_is_cached(date):
    """Check if a specific date exists in cache."""
    try:
        is_cached = storage_service.is_date_cached(date)
        return jsonify({"success": True, "is_cached": is_cached})

    except Exception as e:
        logger.error(
            "error date=%s error=%s",
            date, repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@app.route("/api/debug/supabase-url", methods=["GET"])
def debug_supabase_url():
    """Return SUPABASE_URL of the connected Supabase instance for manual-test observability."""
    try:
        return jsonify({"success": True, "url": util.resolve_env_var("SUPABASE_URL")})
    except Exception as error:
        logger.exception("debug_supabase_url failed: %s", error)
        return jsonify({"success": False, "error": repr(error)}), 500


@app.route("/api/debug/clear-daily-cache", methods=["POST"])
def debug_clear_daily_cache():
    """Delete daily_cache rows in [start_date, end_date]. Manual-test setup helper."""
    try:
        data = request.get_json()
        deleted_count = storage_service.delete_daily_payloads_range(data['start_date'], data['end_date'])
        return jsonify({"success": True, "deleted_count": deleted_count})
    except Exception as error:
        logger.exception("debug_clear_daily_cache failed: %s", error)
        return jsonify({"success": False, "error": repr(error)}), 500


@app.route("/api/debug/daily-cache-summary", methods=["POST"])
def debug_daily_cache_summary():
    """Flat summary of daily_cache rows in [start_date, end_date] for debug panels."""
    try:
        data = request.get_json()
        summary = storage_service.get_daily_payloads_summary(data['start_date'], data['end_date'])
        return jsonify({"success": True, "summary": summary})
    except Exception as error:
        logger.exception("debug_daily_cache_summary failed: %s", error)
        return jsonify({"success": False, "error": repr(error)}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        threaded=True,
        use_evalex=True,
        use_debugger=False,
    )
