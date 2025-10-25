import logging
from dataclasses import asdict, dataclass
import requests
from markitdown import MarkItDown
from io import BytesIO
import re
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
import unicodedata

import util

logger = logging.getLogger("newsletter_scraper")
md = MarkItDown()


@dataclass
class NewsletterSection:
    order: int
    title: str
    emoji: str | None = None


@dataclass
class NewsletterIssue:
    date: str
    newsletter_type: str
    category: str
    title: str | None
    subtitle: str | None
    sections: list[NewsletterSection]


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


def _is_symbol_only_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    if any(character.isalnum() for character in stripped):
        return False

    has_symbol = False

    for character in stripped:
        category = unicodedata.category(character)

        if category.startswith("P"):
            return False

        if category in {"So", "Sk"}:
            has_symbol = True
            continue

        if category in {"Mn", "Me", "Cf", "Cc"}:
            continue

        if category.startswith("Z"):
            continue

        return False

    return has_symbol


def _build_scrape_response(
    start_date,
    end_date,
    dates,
    all_articles,
    url_set,
    issue_metadata_by_key,
    network_fetches,
):
    for article in all_articles:
        article["removed"] = bool(article.get("removed", False))

    grouped_articles: dict[str, list[dict]] = {}
    for article in all_articles:
        date_value = article["date"]
        if isinstance(date_value, str):
            article_date = date_value
        else:
            article_date = util.format_date_for_url(date_value)

        grouped_articles.setdefault(article_date, []).append(article)

    output = _format_final_output(
        start_date, end_date, grouped_articles, issue_metadata_by_key
    )

    articles_data: list[dict] = []
    for article in all_articles:
        payload = {
            "url": article["url"],
            "title": article["title"],
            "date": article["date"],
            "category": article["category"],
            "removed": bool(article.get("removed", False)),
        }
        if article.get("section_title"):
            payload["section_title"] = article["section_title"]
        if article.get("section_emoji"):
            payload["section_emoji"] = article["section_emoji"]
        if article.get("section_order") is not None:
            payload["section_order"] = article["section_order"]
        if article.get("newsletter_type"):
            payload["newsletter_type"] = article["newsletter_type"]
        articles_data.append(payload)

    issues_output = sorted(
        issue_metadata_by_key.values(),
        key=lambda issue: (issue.get("date", ""), issue.get("category", "")),
        reverse=True,
    )

    return {
        "success": True,
        "output": output,
        "articles": articles_data,
        "issues": issues_output,
        "stats": {
            "total_articles": len(all_articles),
            "unique_urls": len(url_set),
            "dates_processed": len(dates),
            "dates_with_content": len(grouped_articles),
            "network_fetches": network_fetches,
            "cache_mode": "read_write",
            "debug_logs": list(util.LOGS),
        },
    }


def _format_final_output(
    start_date, end_date, grouped_articles, issues_by_key
):
    """Format the final output according to requirements.

    >>> grouped = {
    ...     "2024-01-02": [
    ...         {
    ...             "category": "TLDR Tech",
    ...             "title": "Example (1 minute read)",
    ...             "url": "https://example.com/second",
    ...             "section_order": 1,
    ...         }
    ...     ]
    ... }
    >>> issues = {
    ...     ("2024-01-02", "TLDR Tech"): {
    ...         "sections": [
    ...             {"order": 1, "title": "Alpha", "emoji": "🚀"}
    ...         ]
    ...     }
    ... }
    >>> result = _format_final_output(
    ...     datetime(2024, 1, 2), datetime(2024, 1, 2), grouped, issues
    ... )
    >>> "##### 🚀 Alpha" in result
    True
    """

    output = f"# TLDR Newsletter Articles ({util.format_date_for_url(start_date)} to {util.format_date_for_url(end_date)})\n\n"

    sorted_dates = sorted(grouped_articles.keys(), reverse=True)

    def build_article_lines(article_list):
        if not article_list:
            return ""

        lines: list[str] = []
        for index, article in enumerate(article_list, 1):
            domain_name = util.get_domain_name(article["url"])
            is_removed = article.get("removed", False)

            if is_removed:
                title = article["title"]
                title = re.sub(
                    r"\s*\(\d+\s+minutes?\s+read\)", "", title, flags=re.IGNORECASE
                )
                if len(title) > 10:
                    title = title[:10] + "..."
                title_with_domain = f"{title} ({domain_name})"
            else:
                title_with_domain = f"{article['title']} ({domain_name})"

            removed_marker = "?data-removed=true" if is_removed else ""
            lines.append(
                f"{index}. [{title_with_domain}]({article['url']}{removed_marker})"
            )

        return "\n".join(lines) + "\n\n"

    for date_str in sorted_dates:
        articles = grouped_articles[date_str]

        output += f"### {date_str}\n\n"

        category_groups = {}
        for article in articles:
            category = article["category"]
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(article)

        base_order = ["TLDR AI", "TLDR Tech"]
        category_order = [c for c in base_order if c in category_groups]
        extra_categories = [c for c in category_groups if c not in category_order]
        category_order.extend(sorted(extra_categories))

        for category in category_order:
            category_articles = category_groups[category]

            output += f"#### {category}\n\n"

            issue = issues_by_key.get((date_str, category), {})
            issue_title = (issue or {}).get("title")
            issue_subtitle = (issue or {}).get("subtitle")

            if issue_title:
                output += f"_{issue_title}_\n\n"
            if issue_subtitle and issue_subtitle != issue_title:
                output += f"_{issue_subtitle}_\n\n"

            sections = (issue or {}).get("sections") or []
            sections_by_order = {
                section.get("order"): section
                for section in sections
                if section.get("order") is not None
            }

            if sections_by_order:
                articles_by_order: dict[int, list] = {}
                remaining_articles: list[dict] = []

                for article in category_articles:
                    order = article.get("section_order")
                    if order is None or order not in sections_by_order:
                        remaining_articles.append(article)
                        continue
                    articles_by_order.setdefault(order, []).append(article)

                sorted_sections = sorted(
                    sections,
                    key=lambda section: section.get("order", 0),
                )

                for section in sorted_sections:
                    order = section.get("order")
                    section_articles = articles_by_order.get(order, [])
                    if not section_articles:
                        continue

                    header_text = section.get("title") or ""
                    emoji = section.get("emoji")
                    if emoji:
                        header_text = f"{emoji} {header_text}".strip()

                    if header_text:
                        output += f"##### {header_text}\n\n"

                    output += build_article_lines(section_articles)

                if remaining_articles:
                    output += build_article_lines(remaining_articles)
            else:
                output += build_article_lines(category_articles)

    return output


def _parse_articles_from_markdown(markdown, date, newsletter_type):
    """Parse newsletter content into structured metadata and articles.

    >>> sample = '# TLDR AI 2025-10-10\n\n## Gemini Enterprise\n\n🚀\n### Headlines & Launches\n[Example (1 minute read)](https://example.com)'
    >>> parsed = _parse_articles_from_markdown(sample, datetime(2025, 10, 10), "ai")
    >>> parsed["issue"]["sections"][0]["emoji"]
    '🚀'
    """
    lines = markdown.split("\n")
    articles = []
    minute_read_pattern = re.compile(r"\((\d+)\s+minute\s+read\)", re.IGNORECASE)
    github_repo_pattern = re.compile(r"\(GitHub\s+Repo\)", re.IGNORECASE)
    heading_pattern = re.compile(r"^(#+)\s*(.*)$")

    issue_title = None
    issue_subtitle = None
    pending_section_emoji = None
    current_section_order: int | None = None
    section_counter = 0
    sections: list[NewsletterSection] = []
    sections_by_order: dict[int, NewsletterSection] = {}

    if newsletter_type == "tech":
        category = "TLDR Tech"
    elif newsletter_type == "ai":
        category = "TLDR AI"
    else:
        category = f"TLDR {newsletter_type.capitalize()}"

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue

        heading_match = heading_pattern.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()

            if not text:
                continue

            if level == 1 and issue_title is None:
                issue_title = text
                pending_section_emoji = None
                continue

            if level <= 2 and issue_title is not None and issue_subtitle is None:
                issue_subtitle = text
                pending_section_emoji = None
                continue

            if level >= 2:
                if not re.search(r"[A-Za-z0-9]", text):
                    pending_section_emoji = text.strip()
                    continue

                emoji = None
                title_text = text

                split_match = re.match(r"^([^\w\d]+)\s+(.*)$", title_text)
                if split_match and split_match.group(2).strip():
                    potential_emoji = split_match.group(1).strip()
                    remainder = split_match.group(2).strip()
                    if potential_emoji and not re.search(r"[A-Za-z0-9]", potential_emoji):
                        emoji = potential_emoji
                        title_text = remainder

                if pending_section_emoji and not emoji:
                    emoji = pending_section_emoji.strip()

                pending_section_emoji = None

                if not title_text:
                    continue

                section_counter += 1
                section = NewsletterSection(
                    order=section_counter, title=title_text, emoji=emoji or None
                )
                sections.append(section)
                sections_by_order[section_counter] = section
                current_section_order = section_counter
                continue

        if _is_symbol_only_line(line):
            pending_section_emoji = line.strip()
            continue

        link_matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", line)
        for title, url in link_matches:
            if not url.startswith("http"):
                continue

            if _is_file_url(url):
                continue

            if not (
                minute_read_pattern.search(title) or github_repo_pattern.search(title)
            ):
                continue

            cleaned_title = title.strip()
            cleaned_url = url.strip()

            cleaned_title = re.sub(r"^#+\s*", "", cleaned_title)
            cleaned_title = re.sub(r"^\s*\d+\.\s*", "", cleaned_title)

            article = {
                "title": cleaned_title,
                "url": cleaned_url,
                "category": category,
                "date": util.format_date_for_url(date),
                "newsletter_type": newsletter_type,
            }

            if current_section_order is not None:
                section = sections_by_order.get(current_section_order)
                if section is not None:
                    article["section_title"] = section.title
                    if section.emoji:
                        article["section_emoji"] = section.emoji
                    article["section_order"] = current_section_order

            articles.append(article)

    issue_metadata = None
    if issue_title or issue_subtitle or sections:
        issue_metadata = asdict(
            NewsletterIssue(
                date=util.format_date_for_url(date),
                newsletter_type=newsletter_type,
                category=category,
                title=issue_title,
                subtitle=issue_subtitle,
                sections=sections,
            )
        )

    return {"articles": articles, "issue": issue_metadata}


def _fetch_newsletter(date, newsletter_type):
    """Fetch and parse a single newsletter"""
    date_str = util.format_date_for_url(date)
    url = f"https://tldr.tech/{newsletter_type}/{date_str}"

    try:
        net_start = time.time()
        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"},
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
        parsed_content = _parse_articles_from_markdown(
            markdown_content, date, newsletter_type
        )
        articles = parsed_content["articles"]
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
            "issue": parsed_content.get("issue"),
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


def _collect_newsletters_for_date(
    date,
    date_str,
    newsletter_types,
    processed_count,
    total_count,
    url_set,
    all_articles,
    issue_metadata_by_key,
):
    day_articles: list[dict] = []
    day_issues: list[dict] = []
    network_articles = 0
    current_processed = processed_count

    for newsletter_type in newsletter_types:
        current_processed += 1
        util.log(
            f"[newsletter_scraper._collect_newsletters_for_date] Processing {newsletter_type} newsletter for {date_str} ({current_processed}/{total_count})",
            logger=logger,
        )

        result = _fetch_newsletter(date, newsletter_type)
        if result and result["articles"]:
            issue_info = result.get("issue") or {}
            if issue_info:
                issue_copy = json.loads(json.dumps(issue_info))
                issue_category = issue_copy.get("category") or ""
                issue_metadata_by_key[(date_str, issue_category)] = issue_copy
                day_issues.append(issue_copy)

            for article in result["articles"]:
                canonical_url = util.canonicalize_url(article["url"])
                article["url"] = canonical_url

                day_articles.append(article)

                if canonical_url not in url_set:
                    url_set.add(canonical_url)
                    all_articles.append(article)
                    if article.get("fetched_via") == "network":
                        network_articles += 1

        if result and any(
            a.get("fetched_via") == "network"
            for a in (result.get("articles") or [])
        ):
            time.sleep(0.2)

    return current_processed, day_articles, day_issues, network_articles


def scrape_date_range(start_date, end_date):
    """Scrape all newsletters in date range without server-side caching."""
    dates = util.get_date_range(start_date, end_date)
    newsletter_types = ["tech", "ai"]

    all_articles: list[dict] = []
    url_set: set[str] = set()
    processed_count = 0
    total_count = len(dates) * len(newsletter_types)
    network_fetches = 0
    issue_metadata_by_key: dict[tuple[str, str], dict] = {}

    for date in dates:
        date_str = util.format_date_for_url(date)
        (
            processed_count,
            day_articles,
            day_issues,
            network_increment,
        ) = _collect_newsletters_for_date(
            date,
            date_str,
            newsletter_types,
            processed_count,
            total_count,
            url_set,
            all_articles,
            issue_metadata_by_key,
        )
        network_fetches += network_increment

        for article in day_articles:
            article.setdefault("removed", False)

    return _build_scrape_response(
        start_date,
        end_date,
        dates,
        all_articles,
        url_set,
        issue_metadata_by_key,
        network_fetches,
    )
