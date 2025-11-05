"""
TLDR-specific newsletter adapter implementation.

This adapter implements the NewsletterAdapter interface for TLDR newsletters,
handling the specific URL patterns, parsing rules, and content structure of
TLDR Tech and TLDR AI newsletters.
"""

import logging
import re
import time
import unicodedata
from dataclasses import asdict, dataclass

import requests

from newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("tldr_adapter")


@dataclass
class NewsletterSection:
    """Represents a section within a newsletter issue."""

    order: int
    title: str
    emoji: str | None = None


@dataclass
class NewsletterIssue:
    """Represents metadata for a newsletter issue."""

    date: str
    newsletter_type: str
    category: str
    title: str | None
    subtitle: str | None
    sections: list[NewsletterSection]


@dataclass
class ParsedMarkdown:
    """Structured result from parsing markdown once."""

    issue_title: str | None
    issue_subtitle: str | None
    sections: list[NewsletterSection]
    sections_by_order: dict[int, NewsletterSection]
    article_candidates: list[dict]


class TLDRAdapter(NewsletterAdapter):
    """Adapter for TLDR newsletter sources (Tech, AI, etc.)."""

    def fetch_issue(self, date: str, newsletter_type: str) -> str | None:
        """Fetch TLDR newsletter HTML for a specific date and type.

        Args:
            date: Date string in YYYY-MM-DD format
            newsletter_type: Newsletter type (e.g., "tech", "ai")

        Returns:
            HTML content as string, or None if not found
        """
        date_str = util.format_date_for_url(date)

        # Build URL from config pattern
        url = self.config.url_pattern.format(
            base_url=self.config.base_url, type=newsletter_type, date=date_str
        )

        try:
            net_start = time.time()
            response = requests.get(
                url,
                timeout=30,
                headers={"User-Agent": self.config.user_agent},
                allow_redirects=False,
            )
            net_ms = int(round((time.time() - net_start) * 1000))

            if response.status_code == 404:
                return None

            response.raise_for_status()

            if response.is_redirect:
                return None

            util.log(
                f"[tldr_adapter.fetch_issue] Fetched {newsletter_type} for {date_str} in {net_ms}ms",
                logger=logger,
            )

            return response.text

        except requests.RequestException:
            util.log(
                f"[tldr_adapter.fetch_issue] Request error for url={url}",
                level=logging.ERROR,
                exc_info=True,
                logger=logger,
            )
            return None

    def _parse_markdown_structure(
        self, markdown: str, date: str, newsletter_type: str
    ) -> ParsedMarkdown:
        """Parse markdown once into structured format.

        Extracts all structure (headings, sections, links) in a single pass.
        """
        lines = markdown.split("\n")
        heading_pattern = re.compile(r"^(#+)\s*(.*)$")

        issue_title = None
        issue_subtitle = None
        sections: list[NewsletterSection] = []
        sections_by_order: dict[int, NewsletterSection] = {}
        article_candidates: list[dict] = []

        current_section_order: int | None = None
        pending_section_emoji = None
        section_counter = 0
        seen_title = False

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
                    seen_title = True
                    pending_section_emoji = None
                    continue

                if level <= 2 and seen_title and issue_subtitle is None:
                    issue_subtitle = text

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
                        if potential_emoji and not re.search(
                            r"[A-Za-z0-9]", potential_emoji
                        ):
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

            if self._is_symbol_only_line(line):
                pending_section_emoji = line.strip()
                continue

            link_matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", line)
            for title, url in link_matches:
                if not url.startswith("http"):
                    continue
                if self._is_file_url(url):
                    continue

                article_candidates.append(
                    {
                        "title": title,
                        "url": url,
                        "section_order": current_section_order,
                    }
                )

        return ParsedMarkdown(
            issue_title=issue_title,
            issue_subtitle=issue_subtitle,
            sections=sections,
            sections_by_order=sections_by_order,
            article_candidates=article_candidates,
        )

    def parse_articles(
        self, markdown: str, date: str, newsletter_type: str
    ) -> list[dict]:
        """Parse TLDR articles from markdown content.

        Args:
            markdown: Markdown content converted from HTML
            date: Date string for the issue
            newsletter_type: Newsletter type (e.g., "tech", "ai")

        Returns:
            List of article dictionaries
        """
        parsed = self._parse_markdown_structure(markdown, date, newsletter_type)

        article_pattern = re.compile(self.config.article_pattern, re.IGNORECASE)
        category = self.config.category_display_names.get(
            newsletter_type, f"TLDR {newsletter_type.capitalize()}"
        )

        articles = []
        for candidate in parsed.article_candidates:
            if not article_pattern.search(candidate["title"]):
                continue

            cleaned_title = candidate["title"].strip()
            cleaned_title = re.sub(r"^#+\s*", "", cleaned_title)
            cleaned_title = re.sub(r"^\s*\d+\.\s*", "", cleaned_title)

            article = {
                "title": cleaned_title,
                "url": candidate["url"].strip(),
                "category": category,
                "date": util.format_date_for_url(date),
                "newsletter_type": newsletter_type,
            }

            section_order = candidate["section_order"]
            if section_order is not None:
                section = parsed.sections_by_order.get(section_order)
                if section is not None:
                    article["section_title"] = section.title
                    if section.emoji:
                        article["section_emoji"] = section.emoji
                    article["section_order"] = section_order

            articles.append(article)

        return articles

    def extract_issue_metadata(
        self, markdown: str, date: str, newsletter_type: str
    ) -> dict | None:
        """Extract TLDR issue metadata (title, subtitle, sections).

        Args:
            markdown: Markdown content converted from HTML
            date: Date string for the issue
            newsletter_type: Newsletter type (e.g., "tech", "ai")

        Returns:
            Dictionary with issue metadata, or None if no metadata found
        """
        parsed = self._parse_markdown_structure(markdown, date, newsletter_type)

        if not parsed.issue_title and not parsed.issue_subtitle and not parsed.sections:
            return None

        category = self.config.category_display_names.get(
            newsletter_type, f"TLDR {newsletter_type.capitalize()}"
        )

        metadata_sections = parsed.sections
        if parsed.issue_subtitle and parsed.sections:
            subtitle_text = parsed.issue_subtitle
            if parsed.sections[0].title == subtitle_text:
                metadata_sections = parsed.sections[1:]

        issue = NewsletterIssue(
            date=util.format_date_for_url(date),
            newsletter_type=newsletter_type,
            category=category,
            title=parsed.issue_title,
            subtitle=parsed.issue_subtitle,
            sections=metadata_sections,
        )

        return asdict(issue)

    @staticmethod
    def _is_symbol_only_line(text: str) -> bool:
        """Check if a line contains only symbols/emoji (no alphanumeric chars).

        Args:
            text: Text to check

        Returns:
            True if line contains only symbols
        """
        stripped = text.strip()
        if not stripped:
            return False

        if any(character.isalnum() for character in stripped):
            return False

        has_symbol = False

        for character in stripped:
            category = unicodedata.category(character)

            # Punctuation means not a pure symbol line
            if category.startswith("P"):
                return False

            # Symbol characters
            if category in {"So", "Sk"}:
                has_symbol = True
                continue

            # Allow modifiers and control chars
            if category in {"Mn", "Me", "Cf", "Cc"}:
                continue

            # Allow whitespace
            if category.startswith("Z"):
                continue

            return False

        return has_symbol

    @staticmethod
    def _is_file_url(url: str) -> bool:
        """Check if URL points to a file (image, PDF, etc.) rather than a web page.

        Args:
            url: URL to check

        Returns:
            True if URL appears to be a file
        """
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
