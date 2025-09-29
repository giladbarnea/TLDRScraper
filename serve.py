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
import json

from blob_newsletter_cache import get_cached_json, put_cached_json
from blob_store import normalize_url_to_pathname
import util
from summarizer import summarize_url
from blob_cache import blob_cached_json
from removed_urls import get_removed_urls, add_removed_url

app = Flask(__name__)
logging.basicConfig(level=util.resolve_env_var("LOG_LEVEL", "INFO"))
logger = logging.getLogger("serve")
md = MarkItDown()


BLOB_CACHE_HITS = 0
BLOB_CACHE_MISSES = 0


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
        global BLOB_CACHE_HITS, BLOB_CACHE_MISSES
        BLOB_CACHE_HITS = BLOB_CACHE_MISSES = 0
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
    """Detect sponsored content based ONLY on bulletproof UTM parameter combinations.
    
    This function only uses explicit, unambiguous UTM indicators that definitively
    signal paid/sponsored placement. Title-based filtering (is_sponsored_link) handles
    the rest via "(Sponsor)" markers in article titles.
    
    Bulletproof rules:
    - utm_medium contains explicit paid/sponsored terms (thirdparty_advertising, paid, sponsor, etc.)
    - utm_content or utm_term explicitly says "paid"
    """
    try:
        import urllib.parse as urlparse

        parsed = urlparse.urlparse(url)
        query_params = {
            k.lower(): v for k, v in urlparse.parse_qs(parsed.query).items()
        }
        
        # Check utm_medium for EXPLICIT sponsored indicators
        medium_values = [v.lower() for v in query_params.get("utm_medium", [])]
        medium_str = ' '.join(medium_values)
        
        # These are unambiguous paid placement indicators
        explicit_paid_mediums = [
            'thirdparty_advertising',  # Explicitly says it's third-party advertising
            'paid',                     # Explicitly says it's paid
            'sponsor',                  # Explicitly says it's sponsored
            'sponsored',                # Explicitly says it's sponsored
            'cpc',                      # Cost-per-click (paid)
            'cpm',                      # Cost-per-mille (paid)
        ]
        
        if any(indicator in medium_str for indicator in explicit_paid_mediums):
            return True
        
        # Check utm_content or utm_term for explicit "paid" indicator
        content_values = [v.lower() for v in query_params.get("utm_content", [])]
        term_values = [v.lower() for v in query_params.get("utm_term", [])]
        
        if 'paid' in ' '.join(content_values) or 'paid' in ' '.join(term_values):
            return True
        
        # That's it! Everything else is handled by title-based filtering
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
    try:
        from summarizer import _fetch_summarize_prompt

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
    """Summarize a given URL: fetch HTML, convert to Markdown, insert into template, call OpenAI."""
    try:
        data = request.get_json() or {}
        url = (data.get("url") or "").strip()

        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return jsonify({"success": False, "error": "Invalid or missing url"}), 400

        summary = summarize_url(url)

        base_path = normalize_url_to_pathname(url)
        base = base_path[:-3] if base_path.endswith(".md") else base_path
        summary_blob_pathname = f"{base}-summary.md"
        blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
        summary_blob_url = (
            f"{blob_base_url}/{summary_blob_pathname}" if blob_base_url else None
        )

        debug_appendix = (
            f"\n\n---\n"
            f"Debug: Summary cache key candidate\n"
            f"- candidate: `{summary_blob_pathname}`\n"
        )

        return jsonify({
            "success": True,
            "summary_markdown": summary + debug_appendix,
            "summary_blob_url": summary_blob_url,
            "summary_blob_pathname": summary_blob_pathname,
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

        canonical = canonicalize_url(url)
        success = add_removed_url(canonical)

        if success:
            return jsonify({"success": True, "canonical_url": canonical})
        else:
            return jsonify({"success": False, "error": "Failed to persist removal"}), 500

    except Exception as e:
        util.log(
            "[serve.remove_url_endpoint] error error=%s",
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

        # Get all dates in range
        dates = get_date_range(start_date, end_date)
        
        # Try to delete each day's cache file
        from blob_store import delete_file
        
        deleted_count = 0
        failed_count = 0
        errors = []
        
        for date in dates:
            date_str = format_date_for_url(date)
            pathname = _scrape_day_pathname(date_str)
            
            try:
                success = delete_file(pathname)
                if success:
                    deleted_count += 1
                    util.log(
                        f"[serve.invalidate_cache_endpoint] Deleted cache for day={date_str}",
                        logger=logger,
                    )
                else:
                    failed_count += 1
                    errors.append(f"{date_str}: delete returned false")
            except Exception as e:
                failed_count += 1
                error_msg = f"{date_str}: {repr(e)}"
                errors.append(error_msg)
                util.log(
                    f"[serve.invalidate_cache_endpoint] Failed to delete cache for day={date_str} error={repr(e)}",
                    level=logging.WARNING,
                    logger=logger,
                )
        
        return jsonify({
            "success": True,
            "deleted": deleted_count,
            "failed": failed_count,
            "total_days": len(dates),
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


def get_utm_source_category(url):
    """Extract UTM source from URL and map to category"""
    import urllib.parse as urlparse

    try:
        parsed = urlparse.urlparse(url)
        query_params = urlparse.parse_qs(parsed.query)
        utm_source = query_params.get("utm_source", [""])[0].lower()

        # Map UTM sources to categories - accept all TLDR newsletter types
        if utm_source.startswith("tldr"):
            # Map known sources to specific categories
            if utm_source in ["tldrai", "tldr-ai", "tldr_ai"]:
                return "TLDR AI"
            elif utm_source in ["tldr", "tldrtech"]:
                return "TLDR Tech"
            else:
                # For other TLDR sources (tldrmarketing, tldrfounders, etc.),
                # return a category based on the source name
                # Convert tldrmarketing -> TLDR Marketing, tldrfounders -> TLDR Founders, etc.
                suffix = utm_source[4:]  # Remove "tldr" prefix
                category_name = f"TLDR {suffix.capitalize()}"
                return category_name
        else:
            return None  # Filter out non-TLDR sources

    except Exception:
        util.log(
            "[serve.get_utm_source_category] error url=%s",
            url,
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
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
    global BLOB_CACHE_HITS, BLOB_CACHE_MISSES
    cache_start = time.time()
    cached = get_cached_json(newsletter_type, date)
    if cached is not None and cached.get("status") == "hit":
        BLOB_CACHE_HITS += 1
        cached_articles = cached.get("articles", [])
        for a in cached_articles:
            a["fetched_via"] = "hit"
            a["timing_total_ms"] = int(round((time.time() - cache_start) * 1000))
        util.log(
            f"[serve.fetch_newsletter] cache HIT date={date_str} type={newsletter_type} count={len(cached_articles)}",
            logger=logger,
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

        # Always write to blob cache for fast repeats
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
                util.log(
                    "[serve.fetch_newsletter] error sanitizing article url=%s error=%s",
                    a["url"],
                    repr(e),
                    level=logging.WARNING,
                    logger=logger,
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
            ok = put_cached_json(newsletter_type, date, payload)
            util.log(
                f"[serve.fetch_newsletter] wrote cache date={date_str} type={newsletter_type} count={len(sanitized_articles)} ok={bool(ok)}",
                logger=logger,
            )
        except Exception as e:
            util.log(
                "[serve.fetch_newsletter] failed writing cache date=%s type=%s error=%s",
                date_str,
                newsletter_type,
                repr(e),
                level=logging.ERROR,
                exc_info=True,
                logger=logger,
            )

        return result

    except requests.RequestException:
        util.log(
            "[serve.fetch_newsletter] request error url=%s",
            url,
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return None


def canonicalize_url(url) -> str:
    """Canonicalize URL for better deduplication"""
    import urllib.parse as urlparse

    parsed = urlparse.urlparse(url)
    # Keep only the base URL without query parameters for deduplication
    canonical = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path}"
    # Remove trailing slash for consistency
    if canonical.endswith("/") and len(canonical) > 1:
        canonical = canonical[:-1]
    return canonical


def _scrape_day_pathname(date_str: str) -> str:
    """Generate blob pathname for a single day's scrape results."""
    return f"scrape-day-{date_str}.json"


def _get_cached_day(date_str: str):
    """Retrieve cached scrape results for a single day."""
    pathname = _scrape_day_pathname(date_str)
    blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
    
    if not blob_base_url:
        return None
    
    blob_url = f"{blob_base_url}/{pathname}"
    try:
        util.log(
            f"[serve._get_cached_day] Trying cache for day={date_str} pathname={pathname}",
            logger=logger,
        )
        resp = requests.get(
            blob_url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Scraper/1.0)"},
        )
        resp.raise_for_status()
        util.log(
            f"[serve._get_cached_day] Cache HIT for day={date_str}",
            logger=logger,
        )
        return json.loads(resp.content.decode("utf-8"))
    except Exception as e:
        util.log(
            f"[serve._get_cached_day] Cache MISS for day={date_str} - {repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )
        return None


def _put_cached_day(date_str: str, articles: list):
    """Cache scrape results for a single day."""
    pathname = _scrape_day_pathname(date_str)
    
    try:
        from blob_store import put_file
        
        payload = {
            "date": date_str,
            "articles": articles,
            "cached_at": datetime.now().isoformat(),
        }
        put_file(pathname, json.dumps(payload, indent=2))
        util.log(
            f"[serve._put_cached_day] Cached day={date_str} articles={len(articles)}",
            logger=logger,
        )
        return True
    except Exception as e:
        util.log(
            f"[serve._put_cached_day] Failed to cache day={date_str} - {repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )
        return False


def scrape_date_range(start_date, end_date):
    """Scrape all newsletters in date range, using per-day caching"""
    dates = get_date_range(start_date, end_date)
    newsletter_types = ["tech", "ai"]

    # Get removed URLs once at the start (single source of truth)
    removed_urls = get_removed_urls()
    
    all_articles = []
    url_set = set()  # For deduplication by canonical URL
    processed_count = 0
    total_count = len(dates) * len(newsletter_types)
    # Diagnostics
    hits = 0
    misses = 0
    others = 0
    day_cache_hits = 0
    day_cache_misses = 0

    for date in dates:
        date_str = format_date_for_url(date)
        
        # Try to get cached results for this entire day
        cached_day = _get_cached_day(date_str)
        
        if cached_day is not None and "articles" in cached_day:
            # Use cached results for this day
            day_cache_hits += 1
            cached_articles = cached_day["articles"]
            
            util.log(
                f"[serve.scrape_date_range] Day cache HIT date={date_str} articles={len(cached_articles)} (before filtering removed URLs)",
                logger=logger,
            )
            
            # Add all articles from cache to results, filtering removed URLs
            filtered_count = 0
            for article in cached_articles:
                canonical_url = canonicalize_url(article["url"])
                
                # Skip if this URL has been removed
                if canonical_url in removed_urls:
                    filtered_count += 1
                    continue
                
                if canonical_url not in url_set:
                    url_set.add(canonical_url)
                    # Mark as coming from day cache
                    article["fetched_via"] = "day_cache"
                    all_articles.append(article)
                    hits += 1
            
            if filtered_count > 0:
                util.log(
                    f"[serve.scrape_date_range] Filtered {filtered_count} removed URLs from cached day={date_str}",
                    logger=logger,
                )
            
            processed_count += len(newsletter_types)
            continue
        
        # Cache miss - need to fetch this day's newsletters
        day_cache_misses += 1
        day_articles = []
        
        for newsletter_type in newsletter_types:
            processed_count += 1
            print(
                f"Processing {newsletter_type} newsletter for {date_str} ({processed_count}/{total_count})"
            )

            result = fetch_newsletter(date, newsletter_type)
            if result and result["articles"]:
                # Collect articles for this day
                for article in result["articles"]:
                    canonical_url = canonicalize_url(article["url"])
                    
                    # Add to day_articles for caching
                    day_articles.append(article)
                    
                    # Deduplicate by canonical URL for final results
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
        
        # Cache this day's results for future use
        if day_articles:
            # Sanitize articles before caching (remove timing info, etc.)
            # Also filter out removed URLs at cache time
            sanitized_day_articles = []
            for a in day_articles:
                # Skip removed URLs
                if canonicalize_url(a["url"]) in removed_urls:
                    continue
                    
                clean = {
                    k: v
                    for k, v in a.items()
                    if k != "fetched_via" and not k.startswith("timing_")
                }
                sanitized_day_articles.append(clean)
            
            _put_cached_day(date_str, sanitized_day_articles)
            util.log(
                f"[serve.scrape_date_range] Cached day={date_str} articles={len(sanitized_day_articles)} (after removing filtered URLs)",
                logger=logger,
            )

    # Final defensive filter (should be redundant but ensures consistency)
    all_articles = [
        a for a in all_articles
        if canonicalize_url(a["url"]) not in removed_urls
    ]

    # Group articles by date
    grouped_articles = {}
    for article in all_articles:
        date_str = format_date_for_url(article["date"])
        if date_str not in grouped_articles:
            grouped_articles[date_str] = []
        grouped_articles[date_str].append(article)

    # Format output
    output = format_final_output(start_date, end_date, grouped_articles)

    blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()

    return {
        "success": True,
        "output": output,
        "stats": {
            "total_articles": len(all_articles),
            "unique_urls": len(url_set),
            "dates_processed": len(dates),
            "dates_with_content": len(grouped_articles),
            "day_cache_hits": day_cache_hits,
            "day_cache_misses": day_cache_misses,
            "cache_hits": hits,
            "cache_misses": misses,
            "cache_other": others,
            "blob_cache_hits": BLOB_CACHE_HITS,
            "blob_cache_misses": BLOB_CACHE_MISSES,
            "blob_store_present": bool(blob_base_url),
            "debug_logs": list(util.LOGS),
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
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        threaded=False,
        use_reloader=False,
        use_evalex=True,
        processes=1,
        use_debugger=True,
    )
