"""
Source-agnostic newsletter response merger.

This module provides functions to merge responses from multiple newsletter
sources into a single normalized response, without any knowledge of specific
newsletter types or sources.
"""

import re

from newsletter_config import NEWSLETTER_CONFIGS
import util


def build_markdown_output(
    start_date, end_date, grouped_articles: dict[str, list[dict]], issues_by_key: dict
) -> str:
    """Generate neutral markdown output from grouped articles.

    Args:
        start_date: Start date for the range
        end_date: End date for the range
        grouped_articles: Articles grouped by date
        issues_by_key: Issue metadata indexed by (date, source_id, category)

    Returns:
        Markdown formatted string
    """
    start_str = util.format_date_for_url(start_date)
    end_str = util.format_date_for_url(end_date)

    # Neutral header (NO TLDR BRANDING)
    output = f"# Newsletter Articles ({start_str} to {end_str})\n\n"

    # List included sources dynamically
    if issues_by_key:
        sources = sorted(set(issue.get("source_id") for issue in issues_by_key.values() if issue.get("source_id")))
        if sources:
            source_names = [
                NEWSLETTER_CONFIGS[s].display_name
                for s in sources
                if s in NEWSLETTER_CONFIGS
            ]
            if source_names:
                output += f"**Sources:** {', '.join(source_names)}\n\n"

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

        # Group by category
        category_groups = {}
        for article in articles:
            category = article["category"]
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(article)

        # Sort categories by source sort_order
        def get_category_sort_key(category):
            # Find the source_id for this category by looking at articles
            for article in category_groups[category]:
                if article.get("source_id") in NEWSLETTER_CONFIGS:
                    return NEWSLETTER_CONFIGS[article["source_id"]].sort_order
            return 999

        sorted_categories = sorted(category_groups.keys(), key=get_category_sort_key)

        for category in sorted_categories:
            category_articles = category_groups[category]

            output += f"#### {category}\n\n"

            # Find issue metadata for this category
            # Build key as (date, source_id, category) or (date, category) for backwards compat
            issue = None
            if category_articles:
                first_article = category_articles[0]
                source_id = first_article.get("source_id")
                if source_id:
                    issue = issues_by_key.get((date_str, source_id, category))
                if not issue:
                    # Fallback to old key format
                    issue = issues_by_key.get((date_str, category))

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
