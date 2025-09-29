#!/usr/bin/env python3
"""
TLDR Newsletter Scraper Backend with Proxy
"""

from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime, timedelta
import requests
from markitdown import MarkItDown
from io import BytesIO
import re
from bs4 import BeautifulSoup
import time
import os
import threading
import base64
import json

from edge_config_cache import get_cached_json, put_cached_json
from edge_config import (
    is_available as ec_available,
    get_last_write_status,
    get_last_write_body,
    get_effective_env_summary,
)
from blob_store import normalize_url_to_pathname, put_markdown, list_all_entries
import urllib.parse as _urlparse
import collections

app = Flask(__name__)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", os.getenv("TLDR_SCRAPER_LOG_LEVEL", "INFO"))
)
logger = logging.getLogger("serve")
md = MarkItDown()
LOGS = collections.deque(maxlen=200)

# In-memory store for the summarization prompt template fetched from GitHub
SUMMARIZE_PROMPT_TEMPLATE = None
_BLOB_ENTRIES: list[str] = []


def _log(msg, *args, **kwargs):
    try:
        LOGS.append(msg)
    except Exception:
        logger.warning("[serve._log] failed to append to LOGS", exc_info=True)
        pass
    kwargs.setdefault("stacklevel", 2)
    level = kwargs.pop("level", logging.INFO)
    logger.log(level, msg, *args, **kwargs)


def _resolve_github_api_token() -> str:
    return os.getenv("GITHUB_API_TOKEN", os.getenv("TLDR_SCRAPER_GITHUB_API_TOKEN", ""))


def _fetch_summarize_prompt_from_github(
    owner: str = "giladbarnea",
    repo: str = "llm-templates",
    path: str = "text/summarize.md",
    ref: str = "main",
) -> str:
    """Fetch the summarize.md prompt via GitHub Contents API and return it as text."""
    token = _resolve_github_api_token()
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"
    headers = {
        "Accept": "application/vnd.github.v3.raw",
        "User-Agent": "tldr-scraper/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers, timeout=20)
    if resp.status_code == 200:
        # v3.raw returns file content directly
        return resp.text
    # Fallback to JSON/base64 if server ignored Accept header
    if resp.headers.get("Content-Type", "").startswith("application/json"):
        try:
            data = resp.json()
            if isinstance(data, dict) and "content" in data:
                return base64.b64decode(data["content"]).decode(
                    "utf-8", errors="replace"
                )
        except Exception:
            pass
    raise RuntimeError(f"Failed to fetch summarize.md from GitHub: {resp.status_code}")


def _background_fetch_prompt_once():
    """Background job that fetches the summarize prompt once and stores it in memory."""
    global SUMMARIZE_PROMPT_TEMPLATE
    # Idempotency: if already loaded, do nothing
    if SUMMARIZE_PROMPT_TEMPLATE:
        _log(
            "[startup][_background_fetch_prompt_once] summarize.md template already present, skipping fetch"
        )
        return
    try:
        prompt = _fetch_summarize_prompt_from_github()
        SUMMARIZE_PROMPT_TEMPLATE = prompt
        _log(
            "[startup][_background_fetch_prompt_once] summarize.md template fetched and stored in memory"
        )
    except Exception as e:
        logger.exception(
            "[startup][_background_fetch_prompt_once] Failed to fetch summarize.md: %s",
            e,
        )


# Kick off the background fetch when the module is imported (server startup)
try:
    threading.Thread(target=_background_fetch_prompt_once, daemon=True).start()
except Exception:
    logger.exception("[startup] Failed to start background prompt fetch thread")


def _startup_load_blob_listing_sync():
    """Synchronously list blob entries into memory for debug matching."""
    global _BLOB_ENTRIES
    try:
        pfx = os.getenv("BLOB_STORE_PREFIX", os.getenv("TLDR_SCRAPER_BLOB_STORE_PREFIX", "tldr-scraper-blob")).strip()
        entries = list_all_entries(prefix=pfx)
        _BLOB_ENTRIES = entries or []
        _log(f"[startup][_startup_load_blob_listing_sync] loaded blob entries count={len(_BLOB_ENTRIES)} prefix={pfx}")
    except Exception as e:
        _log(
            "[startup][_startup_load_blob_listing_sync] failed to list blobs error=%s",
            repr(e),
            level=logging.WARNING,
        )


# Perform synchronous load immediately at import time (safe if token missing; it no-ops)
_startup_load_blob_listing_sync()

# Per-request run diagnostics (simple globals, reset at start of scrape)
EDGE_READ_ATTEMPTS = 0
EDGE_READ_HITS = 0
EDGE_WRITE_ATTEMPTS = 0
EDGE_WRITE_SUCCESS = 0


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

        _log(
            f"[serve.scrape_newsletters] start start_date={data['start_date']} end_date={data['end_date']}"
        )
        # reset run diagnostics
        global \
            EDGE_READ_ATTEMPTS, \
            EDGE_READ_HITS, \
            EDGE_WRITE_ATTEMPTS, \
            EDGE_WRITE_SUCCESS
        EDGE_READ_ATTEMPTS = EDGE_READ_HITS = EDGE_WRITE_ATTEMPTS = (
            EDGE_WRITE_SUCCESS
        ) = 0
        result = scrape_date_range(start_date, end_date)
        _log(
            f"[serve.scrape_newsletters] done dates_processed={result['stats']['dates_processed']} total_articles={result['stats']['total_articles']}"
        )
        return jsonify(result)

    except Exception as e:
        logger.exception(
            "[serve.scrape_newsletters] Failed to scrape newsletters: %s", e
        )
        return jsonify({"success": False, "error": str(e)}), 500


def get_date_range(start_date, end_date):
    """Generate list of dates between start and end (inclusive)"""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def format_date_for_url(date):
    """Format date as YYYY-MM-DD for TLDR URL"""
    if isinstance(date, str):
        return date
    return date.strftime("%Y-%m-%d")


def is_sponsored_section(text):
    """Check if a section header indicates sponsored content"""
    sponsored_indicators = [
        "sponsor",
        "sponsored",
        "advertisement",
        "advertise",
        "partner",
        "tldr deals",
        "deals",
        "promo",
        "promotion",
    ]
    return any(indicator in text.lower() for indicator in sponsored_indicators)


def is_sponsored_link(title, url):
    """Check if a link appears to be sponsored content"""
    # Only check title for explicit sponsored indicators, not URL UTM params
    # since TLDR articles legitimately use UTM tracking
    sponsored_keywords = [
        "sponsor",
        "sponsored",
        "advertisement",
        "advertise",
        "partner content",
        "affiliate",
        "promo",
        "promotion",
    ]

    title_lower = title.lower()
    return any(keyword in title_lower for keyword in sponsored_keywords)


def is_sponsored_url(url: str) -> bool:
    """Treat links as sponsored based on UTM query params.

    Rules:
    - If utm_medium=newsletter (case-insensitive) => sponsored
    - If utm_campaign is present (any value) => sponsored
    """
    try:
        import urllib.parse as urlparse

        parsed = urlparse.urlparse(url)
        query_params = {
            k.lower(): v for k, v in urlparse.parse_qs(parsed.query).items()
        }
        medium_values = [v.lower() for v in query_params.get("utm_medium", [])]
        if "newsletter" in medium_values:
            return True
        if "utm_campaign" in query_params:
            return True
        return False
    except Exception:
        return False


def extract_newsletter_content(html):
    """Extract newsletter content from HTML using BeautifulSoup"""
    soup = BeautifulSoup(html, "html.parser")

    # Find the main newsletter content area
    # TLDR typically has the content in specific containers
    content_selectors = [
        '[id*="content"]',
        '[class*="newsletter"]',
        '[class*="content"]',
        "main",
        "article",
        ".container",
    ]

    newsletter_content = None
    for selector in content_selectors:
        newsletter_content = soup.select_one(selector)
        if newsletter_content:
            break

    if not newsletter_content:
        newsletter_content = soup.body or soup

    # Convert to markdown
    content_html = str(newsletter_content)
    content_stream = BytesIO(content_html.encode("utf-8"))
    result = md.convert_stream(content_stream, file_extension=".html")

    return result.text_content


def _resolve_openai_api_token() -> str:
    return os.getenv("OPENAI_API_TOKEN", os.getenv("TLDR_SCRAPER_OPENAI_API_TOKEN", ""))


def _convert_html_to_markdown(html: str) -> str:
    """Convert raw HTML to Markdown using MarkItDown."""
    try:
        stream = BytesIO(html.encode("utf-8", errors="ignore"))
        result = md.convert_stream(stream, file_extension=".html")
        return result.text_content
    except Exception:
        return ""


def _insert_page_markdown_into_prompt(template_text: str, page_md: str) -> str:
    """Insert page_md between <summarize this> tags in template_text."""
    if not template_text:
        return f"<summarize this>\n{page_md}\n</summarize this>"
    open_tag_index = template_text.find("<summarize this>")
    if open_tag_index == -1:
        _log(
            "[serve._insert_page_markdown_into_prompt] template_text is not empty but no <summarize this> tag found in template_text: %s",
            template_text,
            level=logging.WARNING,
        )
        return (
            template_text.rstrip()
            + f"\n\n<summarize this>\n{page_md}\n</summarize this>\n"
        )
    close_tag_index = template_text.find("</summarize this>", open_tag_index)
    return (
        template_text[:open_tag_index]
        + page_md
        + template_text[close_tag_index + len("</summarize this>") :]
    )


def _call_openai_responses_api(prompt_text: str) -> str:
    """Call OpenAI Responses API with gpt-5, low reasoning effort, no stream, return text."""
    api_key = _resolve_openai_api_token()
    if not api_key:
        raise RuntimeError("OPENAI_API_TOKEN not set")
    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": "gpt-5",
        # Per official Responses API, `input` can be a string or content array.
        # Use simple string input for text-only requests.
        "input": prompt_text,
        # Reasoning knobs
        "reasoning": {"effort": "low"},
        "stream": False,
    }
    # from IPython import embed; embed()
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=600)
    try:
        resp.raise_for_status()
    except Exception:
        logger.exception(
            "[serve._call_openai_responses_api] request failed url=%s", url
        )
        raise
    data = resp.json()
    problems: list[Exception] = []

    # Extract text from Responses API variants
    # 1) output_text (string or list)
    if isinstance(data, dict) and "output_text" in data:
        try:
            if isinstance(data["output_text"], str):
                return data["output_text"]
            if isinstance(data["output_text"], list):
                return "\n".join([
                    str(x) for x in data["output_text"] if isinstance(x, str)
                ])
        except Exception as e:
            problems.append(e)
            pass
    # 2) output -> content[] -> type=output_text
    try:
        outputs = data.get("output") or []
        texts = []
        for item in outputs:
            for c in item.get("content") or []:
                if c.get("type") in ("output_text", "text") and isinstance(
                    c.get("text"), str
                ):
                    texts.append(c["text"])
        if texts:
            return "\n".join(texts)
    except Exception as e:
        problems.append(e)
        pass
    # 3) choices fallback (compat)
    try:
        choices = data.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content")
            if isinstance(content, str):
                return content
    except Exception as e:
        problems.append(e)
        pass
    # As last resort, return entire JSON
    if problems:
        formatted_problems = "\n".join([repr(e) for e in problems])
        _log(
            "[serve._call_openai_responses_api] Parsing response encountered errors. Returning raw JSON of length %d. url=%s problems=%s",
            len(str(data)),
            url,
            formatted_problems,
            level=logging.ERROR,
        )
    return json.dumps(data)


def is_file_url(url):
    """Check if URL points to a file (image, PDF, etc.) rather than a web page"""
    file_extensions = [
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".bmp",  # Images
        ".pdf",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".xls",
        ".xlsx",  # Documents
        ".mp4",
        ".mp3",
        ".avi",
        ".mov",
        ".wav",  # Media files
        ".zip",
        ".tar",
        ".gz",
        ".rar",  # Archives
    ]

    # Remove query parameters to check the actual file path
    url_path = url.split("?")[0].lower()
    return any(url_path.endswith(ext) for ext in file_extensions)


@app.route("/api/prompt", methods=["GET"])
def get_prompt_template():
    """Return the loaded summarize.md prompt (for debugging/inspection)."""
    global SUMMARIZE_PROMPT_TEMPLATE
    # If not loaded yet, try to load synchronously once
    if not SUMMARIZE_PROMPT_TEMPLATE:
        try:
            SUMMARIZE_PROMPT_TEMPLATE = _fetch_summarize_prompt_from_github()
        except Exception as e:
            _log(
                "[serve.get_prompt_template] error loading prompt=%s",
                repr(e),
                level=logging.ERROR,
                exc_info=True,
            )
            if SUMMARIZE_PROMPT_TEMPLATE:
                return (
                    SUMMARIZE_PROMPT_TEMPLATE,
                    200,
                    {"Content-Type": "text/plain; charset=utf-8"},
                )
            return (
                f"Error loading prompt: {e!r}",
                500,
                {"Content-Type": "text/plain; charset=utf-8"},
            )
    return SUMMARIZE_PROMPT_TEMPLATE, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/api/summarize-url", methods=["POST"])
def summarize_url_endpoint():
    """Summarize a given URL: fetch HTML, convert to Markdown, insert into template, call OpenAI."""
    try:
        data = request.get_json() or {}
        target_url = (data.get("url") or "").strip()
        if not target_url or not (
            target_url.startswith("http://") or target_url.startswith("https://")
        ):
            _log(
                "[serve.summarize_url_endpoint] invalid or missing url=%s",
                target_url,
                level=logging.ERROR,
            )
            return jsonify({"success": False, "error": "Invalid or missing url"}), 400
		# Read-first: if a prior summary blob exists, return it immediately
        try:
			_pfx = os.getenv("BLOB_STORE_PREFIX", os.getenv("TLDR_SCRAPER_BLOB_STORE_PREFIX", "tldr-scraper-blob"))
			base_path = normalize_url_to_pathname(target_url, _pfx)
			base = base_path[:-3] if base_path.endswith(".md") else base_path
			summary_blob_pathname = f"{base}.summary.md"
			store_id = os.getenv("BLOB_STORE_ID", os.getenv("TLDR_SCRAPER_BLOB_STORE_ID", "")).strip()
			if store_id:
				summary_blob_url = f"https://{store_id}.public.blob.vercel-storage.com/{summary_blob_pathname}"
				resp = requests.get(summary_blob_url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Summarizer/1.0)"})
				if resp.status_code == 200 and isinstance(resp.text, str) and resp.text.strip():
					_log(
						f"[serve.summarize_url_endpoint] summary cache HIT url={target_url} pathname={summary_blob_pathname}"
					)
                    # Inject debug appendix (do not store this; it's only in response)
                    appendix_lines = [
                        "\n\n---\n",
                        "Debug: Summary cache key candidate and store listing\n",
                        f"- candidate: `{summary_blob_pathname}`\n",
                    ]
                    try:
                        if _BLOB_ENTRIES:
                            appendix_lines.append(f"- store entries ({len(_BLOB_ENTRIES)}):\n")
                            for k in _BLOB_ENTRIES:
                                if isinstance(k, str):
                                    appendix_lines.append(f"  - `{k}`\n")
                        else:
                            appendix_lines.append("- store entries: empty or unavailable\n")
                    except Exception:
                        appendix_lines.append("- store entries: error\n")
                    summary_with_debug = resp.text + "".join(appendix_lines)
                    return jsonify({
                        "success": True,
                        "summary_markdown": summary_with_debug,
                        "summary_blob_url": summary_blob_url,
                        "summary_blob_pathname": summary_blob_pathname,
                        "debug_summary_cache_key": summary_blob_pathname,
                    })
		except Exception as e:
			_log(
				"[serve.summarize_url_endpoint] summary cache read error url=%s error=%s",
				target_url,
				repr(e),
				level=logging.WARNING,
			)
        # Fetch page
        r = requests.get(
            target_url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Summarizer/1.0)"},
        )
        try:
            r.raise_for_status()
        except Exception as e:
            _log(
                "[serve.summarize_url_endpoint] request error url=%s error=%s",
                target_url,
                repr(e),
                level=logging.ERROR,
                exc_info=True,
            )
            return jsonify({
                "success": False,
                "error": f"Network error fetching URL: {repr(e)}",
            }), 502
        html = r.text
        page_md = _convert_html_to_markdown(html) or ""

        # Persist cleaned Markdown to Vercel Blob with deterministic pathname.
        blob_url = None
        blob_pathname = None
        try:
            blob_pathname = normalize_url_to_pathname(
                target_url,
                os.getenv("BLOB_STORE_PREFIX", os.getenv("TLDR_SCRAPER_BLOB_STORE_PREFIX", "tldr-scraper-blob")),
            )
            blob_url = put_markdown(blob_pathname, page_md)
        except Exception as e:
            _log(
                "[serve.summarize_url_endpoint] blob upload failed url=%s error=%s",
                target_url,
                repr(e),
                level=logging.WARNING,
            )
        # Ensure prompt present
        global SUMMARIZE_PROMPT_TEMPLATE
        if not SUMMARIZE_PROMPT_TEMPLATE:
            try:
                SUMMARIZE_PROMPT_TEMPLATE = _fetch_summarize_prompt_from_github()
            except Exception:
                _log(
                    "[serve.summarize_url_endpoint] failed to fetch summarize.md template url=%s",
                    target_url,
                    level=logging.ERROR,
                    exc_info=True,
                )
                pass
        prompt_template = SUMMARIZE_PROMPT_TEMPLATE or ""
        full_prompt = _insert_page_markdown_into_prompt(prompt_template, page_md)
        summary_text = _call_openai_responses_api(full_prompt)
        # Best-effort: persist the LLM-produced summary to Blob storage alongside the page markdown
        summary_blob_url = None
        summary_blob_pathname = None
        try:
            # Derive a deterministic summary pathname based on the page markdown pathname
            if blob_pathname and isinstance(blob_pathname, str):
                base = blob_pathname[:-3] if blob_pathname.endswith(".md") else blob_pathname
                summary_blob_pathname = f"{base}.summary.md"
            else:
                # Fallback: recompute from URL
                _pfx = os.getenv("BLOB_STORE_PREFIX", os.getenv("TLDR_SCRAPER_BLOB_STORE_PREFIX", "tldr-scraper-blob"))
                _base_path = normalize_url_to_pathname(target_url, _pfx)
                base = _base_path[:-3] if _base_path.endswith(".md") else _base_path
                summary_blob_pathname = f"{base}.summary.md"
            summary_blob_url = put_markdown(summary_blob_pathname, summary_text or "")
        except Exception as e:
            _log(
                "[serve.summarize_url_endpoint] summary blob upload failed url=%s error=%s",
                target_url,
                repr(e),
                level=logging.WARNING,
            )
        # Inject debug appendix only in the response body (not stored)
        try:
            appendix_lines = [
                "\n\n---\n",
                "Debug: Summary cache key candidate and store listing\n",
                f"- candidate: `{summary_blob_pathname}`\n" if summary_blob_pathname else "- candidate: <unknown>\n",
            ]
            if _BLOB_ENTRIES:
                appendix_lines.append(f"- store entries ({len(_BLOB_ENTRIES)}):\n")
                for k in _BLOB_ENTRIES:
                    if isinstance(k, str):
                        appendix_lines.append(f"  - `{k}`\n")
            else:
                appendix_lines.append("- store entries: empty or unavailable\n")
            summary_text_with_debug = (summary_text or "") + "".join(appendix_lines)
        except Exception:
            summary_text_with_debug = summary_text

        resp_payload = {
            "success": True,
            "summary_markdown": summary_text_with_debug,
            "blob_url": blob_url,
            "blob_pathname": blob_pathname,
        }
        if summary_blob_url is not None:
            resp_payload["summary_blob_url"] = summary_blob_url
            resp_payload["summary_blob_pathname"] = summary_blob_pathname
            resp_payload["debug_summary_cache_key"] = summary_blob_pathname
        if blob_url is None:
            resp_payload["upload_error"] = "blob upload failed or URL unavailable"
        return jsonify(resp_payload)
    except requests.RequestException as e:
        _log(
            "[serve.summarize_url_endpoint] request error url=%s",
            target_url,
            level=logging.ERROR,
            exc_info=True,
        )
        return jsonify({
            "success": False,
            "error": f"Network error fetching URL: {repr(e)}",
        }), 502
    except Exception as e:
        _log(
            "[serve.summarize_url_endpoint] error url=%s",
            target_url,
            level=logging.ERROR,
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


def get_utm_source_category(url):
    """Extract UTM source from URL and map to category"""
    import urllib.parse as urlparse

    try:
        parsed = urlparse.urlparse(url)
        query_params = urlparse.parse_qs(parsed.query)
        utm_source = query_params.get("utm_source", [""])[0].lower()

        # Map UTM sources to categories - only "general" and AI
        if utm_source in ["tldr", "tldrtech"]:
            return "TLDR Tech"
        elif utm_source in ["tldrai", "tldr-ai", "tldr_ai"]:
            return "TLDR AI"
        else:
            return None  # Filter out other sources

    except Exception:
        _log(
            "[serve.get_utm_source_category] error url=%s",
            url,
            level=logging.ERROR,
            exc_info=True,
        )
        return None


def parse_articles_from_markdown(markdown, date, newsletter_type):
    """Parse articles from markdown content, using UTM source for categorization"""
    lines = markdown.split("\n")
    articles = []
    in_sponsored_section = False

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Detect section headers to skip sponsored sections
        if line.startswith("###") or line.startswith("##"):
            header_text = re.sub(r"^#+\s*", "", line).strip()

            # Check if this is a sponsored section
            if is_sponsored_section(header_text):
                in_sponsored_section = True
                continue
            else:
                in_sponsored_section = False
            continue

        # Skip content in sponsored sections
        if in_sponsored_section:
            continue

        # Extract article links [Title](URL)
        link_matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", line)
        for title, url in link_matches:
            # Skip if URL doesn't start with http (internal links, etc.)
            if not url.startswith("http"):
                continue

            # Skip file URLs (images, PDFs, etc.)
            if is_file_url(url):
                continue

            # Skip if appears to be sponsored in title
            if is_sponsored_link(title, url):
                continue

            # Skip if URL UTM flags indicate sponsorship
            if is_sponsored_url(url):
                continue

            # Get category from UTM source
            category = get_utm_source_category(url)
            if not category:
                continue  # Skip articles that don't match our desired sources

            # Clean up title and URL
            title = title.strip()
            url = url.strip()

            # Clean up title (remove markdown artifacts)
            title = re.sub(r"^#+\s*", "", title)  # Remove leading ###
            title = re.sub(r"^\s*\d+\.\s*", "", title)  # Remove leading numbers

            articles.append({
                "title": title,
                "url": url,
                "category": category,
                "date": date,
                "newsletter_type": newsletter_type,
            })

    return articles


def fetch_newsletter(date, newsletter_type):
    """Fetch and parse a single newsletter"""
    date_str = format_date_for_url(date)
    url = f"https://tldr.tech/{newsletter_type}/{date_str}"

    # Always try Edge cache read first (no Blob fallback)
    global EDGE_READ_ATTEMPTS, EDGE_READ_HITS
    EDGE_READ_ATTEMPTS += 1
    cache_start = time.time()
    cached = get_cached_json(newsletter_type, date)
    if cached is not None and cached.get("status") == "hit":
        EDGE_READ_HITS += 1
        cached_articles = cached.get("articles", [])
        for a in cached_articles:
            a["fetched_via"] = "hit"
            a["timing_total_ms"] = int(round((time.time() - cache_start) * 1000))
        _log(
            f"[serve.fetch_newsletter] cache HIT date={date_str} type={newsletter_type} count={len(cached_articles)}"
        )
        return {
            "date": date,
            "newsletter_type": newsletter_type,
            "articles": cached_articles,
        }

    try:
        net_start = time.time()
        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Scraper/1.0)"},
        )
        net_ms = int(round((time.time() - net_start) * 1000))

        if response.status_code == 404:
            return None

        response.raise_for_status()

        convert_start = time.time()
        markdown_content = extract_newsletter_content(response.text)
        convert_ms = int(round((time.time() - convert_start) * 1000))

        parse_start = time.time()
        articles = parse_articles_from_markdown(markdown_content, date, newsletter_type)
        parse_ms = int(round((time.time() - parse_start) * 1000))
        total_ms = net_ms + convert_ms + parse_ms
        # Tag fetched source for UI: only tag as 'other' when network was used
        fetched_status = "other"
        for a in articles:
            a["fetched_via"] = fetched_status
            a["timing_total_ms"] = total_ms
            a["timing_fetch_ms"] = net_ms
            a["timing_convert_ms"] = convert_ms
            a["timing_parse_ms"] = parse_ms
        result = {
            "date": date,
            "newsletter_type": newsletter_type,
            "articles": articles,
        }

        # Always write to Edge for fast repeats (per env rules handled in put_cached_json)
        def _sanitize(a):
            clean = {
                k: v
                for k, v in a.items()
                if k != "fetched_via" and not k.startswith("timing_")
            }
            try:
                if "date" in clean and not isinstance(clean["date"], str):
                    clean["date"] = format_date_for_url(clean["date"])
                # Strip utm_* params from stored URLs
                if "url" in clean and isinstance(clean["url"], str):
                    import urllib.parse as urlparse

                    p = urlparse.urlparse(clean["url"])
                    # Keep only non-utm_* query params
                    query_pairs = [
                        (k, v)
                        for (k, v) in urlparse.parse_qsl(
                            p.query, keep_blank_values=True
                        )
                        if not k.lower().startswith("utm_")
                    ]
                    new_query = urlparse.urlencode(query_pairs, doseq=True)
                    clean["url"] = urlparse.urlunparse((
                        p.scheme,
                        p.netloc.lower(),
                        p.path.rstrip("/")
                        if len(p.path) > 1 and p.path.endswith("/")
                        else p.path,
                        p.params,
                        new_query,
                        p.fragment,
                    ))
            except Exception as e:
                _log(
                    "[serve.fetch_newsletter] error sanitizing article url=%s error=%s",
                    a["url"],
                    repr(e),
                    level=logging.WARNING,
                )
                pass
            return clean

        sanitized_articles = [_sanitize(a) for a in articles]
        payload = {
            "status": "hit",
            "date": date_str,
            "newsletter_type": newsletter_type,
            "articles": sanitized_articles,
        }
        try:
            global EDGE_WRITE_ATTEMPTS, EDGE_WRITE_SUCCESS
            EDGE_WRITE_ATTEMPTS += 1
            ok = put_cached_json(newsletter_type, date, payload)
            if ok:
                EDGE_WRITE_SUCCESS += 1
            status = get_last_write_status()
            body = get_last_write_body()
            _log(
                f"[serve.fetch_newsletter] wrote cache date={date_str} type={newsletter_type} count={len(sanitized_articles)} ok={bool(ok)} status={status} body={(body or '')}"
            )
        except Exception as e:
            _log(
                "[serve.fetch_newsletter] failed writing cache date=%s type=%s error=%s",
                date_str,
                newsletter_type,
                repr(e),
                level=logging.ERROR,
                exc_info=True,
            )

        return result

    except requests.RequestException:
        _log(
            "[serve.fetch_newsletter] request error url=%s",
            url,
            level=logging.ERROR,
            exc_info=True,
        )
        return None


def canonicalize_url(url):
    """Canonicalize URL for better deduplication"""
    import urllib.parse as urlparse

    try:
        parsed = urlparse.urlparse(url)
        # Keep only the base URL without query parameters for deduplication
        canonical = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path}"
        # Remove trailing slash for consistency
        if canonical.endswith("/") and len(canonical) > 1:
            canonical = canonical[:-1]
        return canonical
    except:
        return url.lower()


def scrape_date_range(start_date, end_date):
    """Scrape all newsletters in date range"""
    dates = get_date_range(start_date, end_date)
    newsletter_types = ["tech", "ai"]

    all_articles = []
    url_set = set()  # For deduplication by canonical URL
    processed_count = 0
    total_count = len(dates) * len(newsletter_types)
    # Diagnostics
    hits = 0
    misses = 0
    others = 0

    for date in dates:
        for newsletter_type in newsletter_types:
            processed_count += 1
            print(
                f"Processing {newsletter_type} newsletter for {format_date_for_url(date)} ({processed_count}/{total_count})"
            )

            result = fetch_newsletter(date, newsletter_type)
            if result and result["articles"]:
                # Deduplicate by canonical URL
                for article in result["articles"]:
                    canonical_url = canonicalize_url(article["url"])
                    if canonical_url not in url_set:
                        url_set.add(canonical_url)
                        all_articles.append(article)
                        # Count source
                        src = article.get("fetched_via")
                        if src == "hit":
                            hits += 1
                        elif src == "miss":
                            misses += 1
                        else:
                            others += 1

            # Rate limiting - be respectful only when we actually fetched from network
            if result and any(
                a.get("fetched_via") == "other" for a in (result.get("articles") or [])
            ):
                time.sleep(0.2)

    # Group articles by date
    grouped_articles = {}
    for article in all_articles:
        date_str = format_date_for_url(article["date"])
        if date_str not in grouped_articles:
            grouped_articles[date_str] = []
        grouped_articles[date_str].append(article)

    # Format output
    output = format_final_output(start_date, end_date, grouped_articles)

    # Edge config ID consistency check (read URL vs ID)
    ec_url = os.getenv(
        "EDGE_CONFIG_CONNECTION_STRING",
        os.getenv("TLDR_SCRAPER_EDGE_CONFIG_CONNECTION_STRING", ""),
    )
    ec_id_env = os.getenv(
        "EDGE_CONFIG_ID", os.getenv("TLDR_SCRAPER_EDGE_CONFIG_ID", "")
    )

    def _extract_id(u: str):
        try:
            p = _urlparse.urlparse(u)
            # path like /ecfg_xxx or /ecfg_xxx/...
            seg = p.path.strip("/").split("/")[0]
            return seg if seg.startswith("ecfg_") else None
        except Exception as e:
            _log(
                "[serve.scrape_date_range] error extracting id from url=%s error=%s",
                u,
                repr(e),
                level=logging.ERROR,
            )
            return None

    ec_id_from_url = _extract_id(ec_url) if ec_url else None

    return {
        "success": True,
        "output": output,
        "stats": {
            "total_articles": len(all_articles),
            "unique_urls": len(url_set),
            "dates_processed": len(dates),
            "dates_with_content": len(grouped_articles),
            "cache_hits": hits,
            "cache_misses": misses,
            "cache_other": others,
            # Env and cache diagnostics
            **get_effective_env_summary(),
            "edge_config_available": bool(ec_available()),
            "edge_id_match": bool(
                ec_id_from_url and ec_id_env and ec_id_from_url == ec_id_env
            ),
            "edge_reads_attempted": EDGE_READ_ATTEMPTS,
            "edge_reads_hit": EDGE_READ_HITS,
            "edge_writes_attempted": EDGE_WRITE_ATTEMPTS,
            "edge_writes_success": EDGE_WRITE_SUCCESS,
            "debug_logs": list(LOGS),
        },
    }


def format_final_output(start_date, end_date, grouped_articles):
    """Format the final output according to requirements"""
    output = f"# TLDR Newsletter Articles ({format_date_for_url(start_date)} to {format_date_for_url(end_date)})\n\n"

    # Sort dates chronologically
    sorted_dates = sorted(grouped_articles.keys())

    for date_str in sorted_dates:
        articles = grouped_articles[date_str]

        # Use H3 for issue dates (as required)
        output += f"### {date_str}\n\n"

        # Group articles by category (TLDR Tech vs TLDR AI)
        category_groups = {}
        for article in articles:
            category = article["category"]
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(article)

        # Sort categories: TLDR Tech first, then TLDR AI
        category_order = []
        if "TLDR Tech" in category_groups:
            category_order.append("TLDR Tech")
        if "TLDR AI" in category_groups:
            category_order.append("TLDR AI")

        for category in category_order:
            category_articles = category_groups[category]

            # Use H4 for categories (TLDR Tech / TLDR AI)
            output += f"#### {category}\n\n"

            # Keep original chronological order within categories
            for i, article in enumerate(category_articles, 1):
                status = article.get("fetched_via")
                if status not in ("hit", "miss", "other"):
                    status = "other"
                # Timing summary
                total_ms = article.get("timing_total_ms")
                if total_ms is not None and status == "other":
                    timing_label = f", {total_ms}ms"
                elif total_ms is not None and status == "hit":
                    timing_label = f", {total_ms}ms"
                else:
                    timing_label = ""
                title_with_status = f"{article['title']} ({status}{timing_label})"
                output += f"{i}. [{title_with_status}]({article['url']})\n"

            output += "\n"

    return output


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
