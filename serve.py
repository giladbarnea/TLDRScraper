#!/usr/bin/env python3
"""
TLDR Newsletter Scraper backend with a proxy.
"""

from flask import Flask, request, jsonify, send_from_directory
import logging
import requests
import os

import util
import tldr_app
import storage_service
from summarizer import DEFAULT_MODEL, DEFAULT_SUMMARY_EFFORT
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
            "Failed to scrape newsletters: %s",
            error,
        )
        return jsonify({"success": False, "error": str(error)}), 500


@app.route("/api/summarize-url", methods=["POST"])
def summarize_url_endpoint(model: str = DEFAULT_MODEL):
    """Create a summary of the content at a URL.

    Requires 'url'. Optional: 'summarize_effort' to set the reasoning effort level, 'model' query param to specify Gemini model.
    """
    try:
        data = request.get_json() or {}
        model_param = request.args.get("model", DEFAULT_MODEL)
        result = tldr_app.summarize_url(
            data.get("url", ""),
            summarize_effort=data.get("summarize_effort", DEFAULT_SUMMARY_EFFORT),
            model=model_param,
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
        payload = storage_service.get_daily_payload(date)
        if payload is None:
            return jsonify({"success": False, "error": "Date not found"}), 404

        return jsonify({"success": True, "payload": payload})

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
