#!/usr/bin/env python3
"""
TLDR Newsletter Scraper backend with a proxy.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import logging
import requests
import os

import util
import tldr_app
from summarizer import DEFAULT_MODEL, DEFAULT_TLDR_REASONING_EFFORT

# Configure Flask to serve React build output
app = Flask(
    __name__,
    static_folder='static/dist/assets',
    static_url_path='/assets'
)
logging.basicConfig(level=util.resolve_env_var("LOG_LEVEL", "INFO"))
logger = logging.getLogger("serve")


@app.route("/")
def index():
    """Serve the React app"""
    static_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'dist')
    return send_from_directory(static_dist, 'index.html')


@app.route("/api/scrape", methods=["POST"])
def scrape_newsletters_in_date_range():
    """Backend proxy to scrape newsletters. Expects start_date, end_date, excluded_urls, and optionally sources in the request body."""
    try:
        data = request.get_json()
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
            "[serve.scrape_newsletters_in_date_range] Failed to scrape newsletters: %s",
            error,
        )
        return jsonify({"success": False, "error": str(error)}), 500


@app.route("/api/tldr-url", methods=["POST"])
def tldr_url(model: str = DEFAULT_MODEL):
    """Create a TLDR of the content at a URL.

    Requires 'url'. Optional: 'summary_effort' to set the reasoning effort level, 'model' query param to specify OpenAI model.
    """
    try:
        data = request.get_json() or {}
        model_param = request.args.get("model", DEFAULT_MODEL)
        result = tldr_app.tldr_url(
            data.get("url", ""),
            summary_effort=data.get("summary_effort", DEFAULT_TLDR_REASONING_EFFORT),
            model=model_param,
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
