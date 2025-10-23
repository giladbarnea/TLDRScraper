#!/usr/bin/env python3
"""
TLDR Newsletter Scraper backend with a proxy.
Important: cli.py must expose the exact same interfaces to the app logic that serve.py exposes via the web. Any changes made here must also be mirrored in cli.py and verified through cli.py.
"""

from flask import Flask, render_template, request, jsonify
import logging
import requests

import util
import tldr_app

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

    Requires 'url'. Optional: 'summary_effort' to set the reasoning effort level.
    """
    try:
        data = request.get_json() or {}
        result = tldr_app.summarize_url(
            data.get("url", ""),
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

    Requires 'url'. Optional: 'summary_effort' to set the reasoning effort level.
    """
    try:
        data = request.get_json() or {}
        result = tldr_app.tldr_url(
            data.get("url", ""),
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
