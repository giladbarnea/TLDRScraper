import logging
import requests
from markitdown import MarkItDown
from io import BytesIO
import re
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime

import util
from blob_store import build_scraped_day_cache_key
from removed_urls import get_removed_urls
import cache_mode

logger = logging.getLogger("newsletter_scraper")
md = MarkItDown()


def _is_file_url(url):
    """Check if URL points to a file (image, PDF, etc.) rather than a web page"""
    file_extensions = [
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".bmp",
        ".pdf",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".xls",
        ".xlsx",
        ".mp4",
        ".mp3",
        ".avi",
        ".mov",
        ".wav",
        ".zip",
        ".tar",
        ".gz",
        ".rar",
    ]

    url_path = url.split("?")[0].lower()
    return any(url_path.endswith(ext) for ext in file_extensions)


def _extract_newsletter_content(html):
    """Extract newsletter content from HTML using BeautifulSoup"""
    soup = BeautifulSoup(html, "html.parser")

    newsletter_content = soup.body or soup

    content_html = str(newsletter_content)
    content_stream = BytesIO(content_html.encode("utf-8"))
    result = md.convert_stream(content_stream, file_extension=".html")

    return result.text_content


def _get_cached_day(date_str: str):
    """Retrieve cached scrape results for a single day."""
    if not cache_mode.can_read():
        return None

    pathname = build_scraped_day_cache_key(date_str)
    blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()

    if not blob_base_url:
        return None

    blob_url = f"{blob_base_url}/{pathname}"
    try:
        util.log(
            f"[newsletter_scraper._get_cached_day] Trying cache for day={date_str} pathname={pathname}",
            logger=logger,
        )
        resp = requests.get(
            blob_url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Scraper/1.0)"},
        )
        resp.raise_for_status()
        util.log(
            f"[newsletter_scraper._get_cached_day] Cache HIT for day={date_str}",
            logger=logger,
        )
        return json.loads(resp.content.decode("utf-8"))
    except Exception as e:
        util.log(
            f"[newsletter_scraper._get_cached_day] Cache MISS for day={date_str} - {repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )
        return None


def _put_cached_day(date_str: str, articles: list):
    """Cache scrape results for a single day."""
    if not cache_mode.can_write():
        return False

    pathname = build_scraped_day_cache_key(date_str)

    try:
        from blob_store import put_file

        payload = {
            "date": date_str,
            "articles": articles,
            "cached_at": datetime.now().isoformat(),
        }
        put_file(pathname, json.dumps(payload, indent=2))
        util.log(
            f"[newsletter_scraper._put_cached_day] Cached day={date_str} articles={len(articles)}",
            logger=logger,
        )
        return True
    except Exception as e:
        util.log(
            f"[newsletter_scraper._put_cached_day] Failed to cache day={date_str} - {repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )
        return False


def _format_final_output(start_date, end_date, grouped_articles):
    """Format the final output according to requirements.

    >>> grouped = {
    ...     "2024-01-02": [
    ...         {
    ...             "category": "TLDR Tech",
    ...             "title": "Second (1 minute read)",
    ...             "url": "https://example.com/second",
    ...         }
    ...     ],
    ...     "2024-01-03": [
    ...         {
    ...             "category": "TLDR Tech",
    ...             "title": "Third (1 minute read)",
    ...             "url": "https://example.com/third",
    ...         }
    ...     ],
    ... }
    >>> result = _format_final_output(
    ...     datetime(2024, 1, 1), datetime(2024, 1, 3), grouped
    ... )
    >>> result.index("2024-01-03") < result.index("2024-01-02")
    True
    """
    output = f"# TLDR Newsletter Articles ({util.format_date_for_url(start_date)} to {util.format_date_for_url(end_date)})\n\n"

    sorted_dates = sorted(grouped_articles.keys(), reverse=True)

    for date_str in sorted_dates:
        articles = grouped_articles[date_str]

        output += f"### {date_str}\n\n"

        category_groups = {}
        for article in articles:
            category = article["category"]
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(article)

        category_order = ["TLDR Tech", "TLDR AI"]
        category_order = [c for c in category_order if c in category_groups]

        for category in category_order:
            category_articles = category_groups[category]

            output += f"#### {category}\n\n"

            for i, article in enumerate(category_articles, 1):
                domain_name = util.get_domain_name(article['url'])
                is_removed = article.get("removed", False)
                
                # Format title based on removed state
                if is_removed:
                    # For removed articles: remove "(N minutes read)" and truncate to 10 chars
                    import re
                    title = article['title']
                    # Remove "(N minutes read)" pattern
                    title = re.sub(r'\s*\(\d+\s+minutes?\s+read\)', '', title, flags=re.IGNORECASE)
                    # Truncate to 10 characters
                    if len(title) > 10:
                        title = title[:10] + '...'
                    title_with_domain = f"{title} ({domain_name})"
                else:
                    # Normal article: include full title with domain
                    title_with_domain = f"{article['title']} ({domain_name})"
                
                # Add data-removed attribute via data URL parameter (will be parsed by frontend)
                removed_marker = f"?data-removed=true" if is_removed else ""
                output += f"{i}. [{title_with_domain}]({article['url']}{removed_marker})\n"

            output += "\n"

    return output


def _parse_articles_from_markdown(markdown, date, newsletter_type):
    """Parse articles from markdown content, filtering by '(X minute read)' pattern"""
    lines = markdown.split("\n")
    articles = []
    minute_read_pattern = re.compile(r"\((\d+)\s+minute\s+read\)", re.IGNORECASE)

    for line in lines:
        line = line.strip()

        if not line:
            continue

        link_matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", line)
        for title, url in link_matches:
            if not url.startswith("http"):
                continue

            if _is_file_url(url):
                continue

            if not minute_read_pattern.search(title):
                continue

            title = title.strip()
            url = url.strip()

            title = re.sub(r"^#+\s*", "", title)
            title = re.sub(r"^\s*\d+\.\s*", "", title)

            if newsletter_type == "tech":
                category = "TLDR Tech"
            elif newsletter_type == "ai":
                category = "TLDR AI"
            else:
                category = f"TLDR {newsletter_type.capitalize()}"

            articles.append({
                "title": title,
                "url": url,
                "category": category,
                "date": util.format_date_for_url(date),
                "newsletter_type": newsletter_type,
            })

    return articles


def _fetch_newsletter(date, newsletter_type):
    """Fetch and parse a single newsletter"""
    date_str = util.format_date_for_url(date)
    url = f"https://tldr.tech/{newsletter_type}/{date_str}"

    try:
        net_start = time.time()
        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Scraper/1.0)"},
            allow_redirects=False,
        )
        net_ms = int(round((time.time() - net_start) * 1000))

        if response.status_code == 404:
            return None

        response.raise_for_status()

        if response.is_redirect:
            return None

        convert_start = time.time()
        markdown_content = _extract_newsletter_content(response.text)
        convert_ms = int(round((time.time() - convert_start) * 1000))

        parse_start = time.time()
        articles = _parse_articles_from_markdown(
            markdown_content, date, newsletter_type
        )
        parse_ms = int(round((time.time() - parse_start) * 1000))
        total_ms = net_ms + convert_ms + parse_ms
        for a in articles:
            a["fetched_via"] = "network"
            a["timing_total_ms"] = total_ms
            a["timing_fetch_ms"] = net_ms
            a["timing_convert_ms"] = convert_ms
            a["timing_parse_ms"] = parse_ms

        return {
            "date": util.format_date_for_url(date),
            "newsletter_type": newsletter_type,
            "articles": articles,
        }

    except requests.RequestException:
        util.log(
            "[newsletter_scraper._fetch_newsletter] request error url=%s",
            url,
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return None


def scrape_date_range(start_date, end_date):
    """Scrape all newsletters in date range, using per-day caching"""
    dates = util.get_date_range(start_date, end_date)
    newsletter_types = ["tech", "ai"]

    removed_urls = get_removed_urls()

    all_articles = []
    url_set = set()
    processed_count = 0
    total_count = len(dates) * len(newsletter_types)
    others = 0
    day_cache_hits = 0
    day_cache_misses = 0

    for date in dates:
        date_str = util.format_date_for_url(date)

        cached_day = _get_cached_day(date_str)

        if cached_day is not None and "articles" in cached_day:
            day_cache_hits += 1
            cached_articles = cached_day["articles"]

            util.log(
                f"[newsletter_scraper.scrape_date_range] Day cache HIT date={date_str} articles={len(cached_articles)}",
                logger=logger,
            )

            for article in cached_articles:
                canonical_url = util.canonicalize_url(article["url"])

                if canonical_url not in url_set:
                    url_set.add(canonical_url)
                    article["fetched_via"] = "day_cache"
                    # Mark as removed if in removed set
                    article["removed"] = article.get("removed", False) or canonical_url in removed_urls
                    all_articles.append(article)

            processed_count += len(newsletter_types)
            continue

        day_cache_misses += 1
        day_articles = []

        for newsletter_type in newsletter_types:
            processed_count += 1
            print(
                f"Processing {newsletter_type} newsletter for {date_str} ({processed_count}/{total_count})"
            )

            result = _fetch_newsletter(date, newsletter_type)
            if result and result["articles"]:
                for article in result["articles"]:
                    canonical_url = util.canonicalize_url(article["url"])

                    day_articles.append(article)

                    if canonical_url not in url_set:
                        url_set.add(canonical_url)
                        # Mark as removed if in removed set
                        article["removed"] = article.get("removed", False) or canonical_url in removed_urls
                        all_articles.append(article)
                        if article.get("fetched_via") == "network":
                            others += 1

            if result and any(
                a.get("fetched_via") == "network"
                for a in (result.get("articles") or [])
            ):
                time.sleep(0.2)

        if day_articles:
            sanitized_day_articles = []
            for a in day_articles:
                clean = {
                    k: v
                    for k, v in a.items()
                    if k != "fetched_via" and not k.startswith("timing_")
                }
                # Mark as removed if in removed set
                canonical_url = util.canonicalize_url(a["url"])
                clean["removed"] = a.get("removed", False) or canonical_url in removed_urls
                sanitized_day_articles.append(clean)

            _put_cached_day(date_str, sanitized_day_articles)
            util.log(
                f"[newsletter_scraper.scrape_date_range] Cached day={date_str} articles={len(sanitized_day_articles)}",
                logger=logger,
            )

    grouped_articles = {}
    for article in all_articles:
        # article["date"] should already be a string, but handle both cases
        date_val = article["date"]
        if isinstance(date_val, str):
            date_str = date_val
        else:
            date_str = util.format_date_for_url(date_val)
        
        if date_str not in grouped_articles:
            grouped_articles[date_str] = []
        grouped_articles[date_str].append(article)

    output = _format_final_output(start_date, end_date, grouped_articles)

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
            "network_fetches": others,
            "blob_store_present": bool(blob_base_url),
            "cache_mode": cache_mode.get_cache_mode().value,
            "debug_logs": list(util.LOGS),
        },
    }
