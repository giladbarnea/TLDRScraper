import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from util import canonicalize_url


class TestCanonicalizeUrl:
    """Test URL canonicalization for deduplication."""

    def test_removes_http_protocol(self):
        assert canonicalize_url("http://example.com") == "example.com"
        assert canonicalize_url("http://example.com/path") == "example.com/path"

    def test_removes_https_protocol(self):
        assert canonicalize_url("https://example.com") == "example.com"
        assert canonicalize_url("https://example.com/path") == "example.com/path"

    def test_removes_www_prefix(self):
        assert canonicalize_url("http://www.example.com") == "example.com"
        assert canonicalize_url("https://www.example.com") == "example.com"
        assert canonicalize_url("https://www.example.com/path") == "example.com/path"

    def test_removes_query_parameters(self):
        assert canonicalize_url("https://example.com/path?query=1") == "example.com/path"
        assert canonicalize_url("https://example.com?foo=bar&baz=qux") == "example.com"

    def test_removes_url_fragments(self):
        assert canonicalize_url("https://example.com/path#section") == "example.com/path"
        assert canonicalize_url("https://example.com#top") == "example.com"

    def test_removes_trailing_slash_non_root(self):
        assert canonicalize_url("https://example.com/path/") == "example.com/path"
        assert canonicalize_url("https://example.com/a/b/c/") == "example.com/a/b/c"

    def test_normalizes_root_trailing_slash(self):
        """Root paths with and without trailing slash should canonicalize the same."""
        canonical_without = canonicalize_url("https://example.com")
        canonical_with = canonicalize_url("https://example.com/")
        assert canonical_without == canonical_with, \
            f"Root paths should match: {canonical_without} != {canonical_with}"

    def test_lowercases_domain(self):
        assert canonicalize_url("https://EXAMPLE.COM") == "example.com"
        assert canonicalize_url("https://Example.Com/Path") == "example.com/Path"

    def test_protocol_less_www_urls(self):
        """Protocol-less URLs with www should still strip www."""
        canonical = canonicalize_url("www.example.com")
        expected = "example.com"
        assert canonical == expected, \
            f"www. should be stripped even without protocol: got {canonical}"

    def test_deduplication_groups(self):
        """URLs that should deduplicate to the same canonical form."""
        variants = [
            "http://example.com",
            "http://www.example.com",
            "https://example.com",
            "https://www.example.com",
            "https://example.com/",
            "https://www.example.com/",
            "example.com",
            "example.com/",
            "www.example.com",
        ]

        canonicals = [canonicalize_url(url) for url in variants]
        unique_canonicals = set(canonicals)

        assert len(unique_canonicals) == 1, \
            f"All variants should canonicalize to same value, got: {unique_canonicals}"

    def test_path_variants_deduplicate(self):
        """URLs with same path but different protocols/www/trailing slashes should merge."""
        variants = [
            "http://example.com/path",
            "http://example.com/path/",
            "http://www.example.com/path",
            "http://www.example.com/path/",
            "https://example.com/path",
            "https://example.com/path/",
            "https://www.example.com/path",
            "https://www.example.com/path/",
            "https://example.com/path?query=1",
            "https://example.com/path#fragment",
        ]

        canonicals = [canonicalize_url(url) for url in variants]
        unique_canonicals = set(canonicals)

        assert len(unique_canonicals) == 1, \
            f"All path variants should canonicalize to same value, got: {unique_canonicals}"

    def test_different_paths_stay_different(self):
        """URLs with different paths should not deduplicate."""
        url1 = "https://example.com/path1"
        url2 = "https://example.com/path2"

        assert canonicalize_url(url1) != canonicalize_url(url2)

    def test_different_domains_stay_different(self):
        """URLs with different domains should not deduplicate."""
        url1 = "https://example.com/path"
        url2 = "https://other.com/path"

        assert canonicalize_url(url1) != canonicalize_url(url2)

    def test_real_world_examples(self):
        """Test with real URLs from newsletter sources."""
        assert canonicalize_url("https://threadreaderapp.com/thread/123") == \
            "threadreaderapp.com/thread/123"

        assert canonicalize_url("https://news.ycombinator.com/item?id=123456") == \
            "news.ycombinator.com/item"

        assert canonicalize_url("https://github.com/user/repo/") == \
            "github.com/user/repo"
