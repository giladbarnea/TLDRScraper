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
        lines = markdown.split("\n")
        articles = []

        # Compile patterns from config
        article_pattern = re.compile(self.config.article_pattern, re.IGNORECASE)
        heading_pattern = re.compile(r"^(#+)\s*(.*)$")

        # Get category display name from config
        category = self.config.category_display_names.get(
            newsletter_type, f"TLDR {newsletter_type.capitalize()}"
        )

        # Section tracking
        pending_section_emoji = None
        current_section_order: int | None = None
        section_counter = 0
        sections: list[NewsletterSection] = []
        sections_by_order: dict[int, NewsletterSection] = {}

        for raw_line in lines:
            line = raw_line.strip()

            if not line:
                continue

            # Check for heading
            heading_match = heading_pattern.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()

                if not text:
                    continue

                # Level 2+ headings can be sections
                if level >= 2:
                    # Check if this is a symbol-only heading (emoji section marker)
                    if not re.search(r"[A-Za-z0-9]", text):
                        pending_section_emoji = text.strip()
                        continue

                    emoji = None
                    title_text = text

                    # Try to extract emoji from the beginning of the heading
                    split_match = re.match(r"^([^\w\d]+)\s+(.*)$", title_text)
                    if split_match and split_match.group(2).strip():
                        potential_emoji = split_match.group(1).strip()
                        remainder = split_match.group(2).strip()
                        if potential_emoji and not re.search(
                            r"[A-Za-z0-9]", potential_emoji
                        ):
                            emoji = potential_emoji
                            title_text = remainder

                    # Use pending emoji if we don't have one yet
                    if pending_section_emoji and not emoji:
                        emoji = pending_section_emoji.strip()

                    pending_section_emoji = None

                    if not title_text:
                        continue

                    # Create section
                    section_counter += 1
                    section = NewsletterSection(
                        order=section_counter, title=title_text, emoji=emoji or None
                    )
                    sections.append(section)
                    sections_by_order[section_counter] = section
                    current_section_order = section_counter
                    continue

            # Check for symbol-only line (emoji section marker)
            if self._is_symbol_only_line(line):
                pending_section_emoji = line.strip()
                continue

            # Look for article links
            link_matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", line)
            for title, url in link_matches:
                if not url.startswith("http"):
                    continue

                if self._is_file_url(url):
                    continue

                # Check if this matches our article pattern
                if not article_pattern.search(title):
                    continue

                cleaned_title = title.strip()
                cleaned_url = url.strip()

                # Clean up title formatting
                cleaned_title = re.sub(r"^#+\s*", "", cleaned_title)
                cleaned_title = re.sub(r"^\s*\d+\.\s*", "", cleaned_title)

                article = {
                    "title": cleaned_title,
                    "url": cleaned_url,
                    "category": category,
                    "date": util.format_date_for_url(date),
                    "newsletter_type": newsletter_type,
                }

                # Add section information if available
                if current_section_order is not None:
                    section = sections_by_order.get(current_section_order)
                    if section is not None:
                        article["section_title"] = section.title
                        if section.emoji:
                            article["section_emoji"] = section.emoji
                        article["section_order"] = current_section_order

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
        lines = markdown.split("\n")
        heading_pattern = re.compile(r"^(#+)\s*(.*)$")

        # Get category display name from config
        category = self.config.category_display_names.get(
            newsletter_type, f"TLDR {newsletter_type.capitalize()}"
        )

        issue_title = None
        issue_subtitle = None
        pending_section_emoji = None
        section_counter = 0
        sections: list[NewsletterSection] = []

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

                # Level 1 heading is the issue title
                if level == 1 and issue_title is None:
                    issue_title = text
                    pending_section_emoji = None
                    continue

                # Level 2 heading (after title) is the subtitle
                if level <= 2 and issue_title is not None and issue_subtitle is None:
                    issue_subtitle = text
                    pending_section_emoji = None
                    continue

                # Level 2+ headings can be sections
                if level >= 2:
                    # Check if this is a symbol-only heading
                    if not re.search(r"[A-Za-z0-9]", text):
                        pending_section_emoji = text.strip()
                        continue

                    emoji = None
                    title_text = text

                    # Try to extract emoji from heading
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
                    continue

            # Check for symbol-only line
            if self._is_symbol_only_line(line):
                pending_section_emoji = line.strip()
                continue

        # Return metadata if we found anything
        if issue_title or issue_subtitle or sections:
            issue = NewsletterIssue(
                date=util.format_date_for_url(date),
                newsletter_type=newsletter_type,
                category=category,
                title=issue_title,
                subtitle=issue_subtitle,
                sections=sections,
            )
            return asdict(issue)

        return None

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
