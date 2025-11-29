"""Tests for util.merge_article_lists state preservation."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from util import merge_article_lists


class TestMergeArticleLists:
    """Test article merging with state preservation."""

    def test_preserves_all_state_fields(self):
        """Existing article's state fields are fully preserved on overlap."""
        existing = [
            {
                "url": "https://example.com/article",
                "title": "Old Title",
                "read": {"isRead": True, "markedAt": "2024-01-01"},
                "removed": False,
                "tldr": {"status": "available", "markdown": "Summary"},
                "custom_field": "preserved",
            }
        ]
        new = [
            {
                "url": "https://example.com/article",
                "title": "New Title",
                "score": 999,  # New field
            }
        ]

        result = merge_article_lists(existing, new)

        assert len(result) == 1, "Should have exactly one article"
        merged = result[0]

        # Verify ALL existing fields preserved
        assert merged["title"] == "Old Title", "Title should be from existing"
        assert merged["read"]["isRead"] is True, "Read state preserved"
        assert merged["removed"] is False, "Removed state preserved"
        assert merged["tldr"]["status"] == "available", "TLDR state preserved"
        assert merged["custom_field"] == "preserved", "Custom field preserved"

        # Verify new fields NOT added
        assert "score" not in merged, "New fields should not be added to existing articles"

    def test_canonical_url_matching(self):
        """Articles matched by canonical URL (trailing slash, www, etc.)."""
        existing = [{"url": "https://www.example.com/article/", "read": True, "id": 1}]
        new = [
            {"url": "https://example.com/article", "read": False, "id": 2}  # Different domain/trailing slash
        ]

        result = merge_article_lists(existing, new)

        # Should be treated as same article
        assert len(result) == 1, "Canonical URLs should match"
        assert result[0]["read"] is True, "Should preserve existing state"
        assert result[0]["id"] == 1, "Should keep existing article entirely"

    def test_adds_only_new_urls(self):
        """New articles added only if URL not in existing."""
        existing = [{"url": "https://a.com", "title": "A"}]
        new = [
            {"url": "https://a.com", "title": "A Updated"},  # Overlap - ignored
            {"url": "https://b.com", "title": "B"},  # New - added
            {"url": "https://c.com", "title": "C"},  # New - added
        ]

        result = merge_article_lists(existing, new)

        assert len(result) == 3, "Should have 3 total articles"
        urls = {a["url"] for a in result}
        assert urls == {"https://a.com", "https://b.com", "https://c.com"}

        # Verify 'a' is the existing one, not new
        a_article = next(a for a in result if "a.com" in a["url"])
        assert a_article["title"] == "A", "Existing article should be preserved"

    def test_empty_lists(self):
        """Handle empty existing and new lists."""
        assert merge_article_lists([], []) == []

        existing = [{"url": "https://a.com"}]
        assert merge_article_lists(existing, []) == existing

        new = [{"url": "https://b.com"}]
        assert merge_article_lists([], new) == new

    def test_preserves_removed_and_read_flags(self):
        """Critical user state flags (removed, read) are never overwritten."""
        existing = [
            {"url": "https://removed.com", "title": "Removed", "removed": True},
            {"url": "https://read.com", "title": "Read", "read": {"isRead": True, "markedAt": "2024-01-01"}},
        ]
        new = [
            {"url": "https://removed.com", "title": "Removed Updated", "removed": False},  # Try to un-remove
            {"url": "https://read.com", "title": "Read Updated", "read": {"isRead": False}},  # Try to un-read
        ]

        result = merge_article_lists(existing, new)

        removed_article = next(a for a in result if "removed.com" in a["url"])
        read_article = next(a for a in result if "read.com" in a["url"])

        assert removed_article["removed"] is True, "Removed flag must be preserved"
        assert read_article["read"]["isRead"] is True, "Read flag must be preserved"
