#!/usr/bin/env python3
"""
TLDR Newsletter Scraper backend with a proxy.
Important: cli.py must expose the exact same interfaces to the app logic that serve.py exposes via the web. Any changes made here must also be mirrored in cli.py and verified through cli.py.
"""

from flask import Flask, render_template, request, jsonify
import logging
import requests
from pathlib import Path

import util
import tldr_app

app = Flask(__name__)
logging.basicConfig(level=util.resolve_env_var("LOG_LEVEL", "INFO"))
logger = logging.getLogger("serve")

_removed_urls_file = Path("removed_urls.json")
_removed_urls_file.touch(exist_ok=True)
if not _removed_urls_file.read_text().strip():
    _removed_urls_file.write_text("[]")


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

        result = tldr_app.scrape_newsletters(
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
        prompt = tldr_app.get_summarize_prompt_template()
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
        result = tldr_app.summarize_url(
            data.get("url", ""),
            cache_only=bool(data.get("cache_only", False)),
            summary_effort=data.get("summary_effort", "low"),
        )

        return jsonify(result)

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
        result = tldr_app.tldr_url(
            data.get("url", ""),
            cache_only=bool(data.get("cache_only", False)),
            summary_effort=data.get("summary_effort", "low"),
        )

        return jsonify(result)

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
        data = request.get_json() or {}
        result = tldr_app.remove_url(data.get("url"))
        return jsonify(result)

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
        return jsonify(tldr_app.list_removed_urls())
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
        return jsonify(tldr_app.get_cache_mode())
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
        result = tldr_app.set_cache_mode(data.get("cache_mode"))
        return jsonify(result)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
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
        result = tldr_app.invalidate_cache_in_date_range(
            data.get("start_date"),
            data.get("end_date"),
        )
        return jsonify(result)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
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
        result = tldr_app.invalidate_cache_for_date(data.get("date"))
        return jsonify(result)

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
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
