"""Tests for newsletter_limiter Max-Min Fairness algorithm."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from newsletter_limiter import calculate_quotas


class TestCalculateQuotas:
    """Test Max-Min Fairness distribution algorithm."""

    @pytest.mark.parametrize(
        "source_counts,limit,expected,test_id",
        [
            # Remainder distribution - verify fair allocation of indivisible remainder
            (
                {"A": 100, "B": 100, "C": 100},
                50,
                {"A": 16, "B": 16, "C": 16},
                "remainder_distributed",
            ),
            # Multi-round waterfilling - fewers in multiple iterations
            (
                {"A": 3, "B": 10, "C": 20, "D": 100},
                50,
                {"A": 3, "B": 10, "C": 18, "D": 18},
                "multi_round_waterfilling",
            ),
            # Limit less than number of sources
            (
                {"A": 100, "B": 100, "C": 100, "D": 100},
                2,
                {"A": 0, "B": 0, "C": 0, "D": 0},
                "limit_less_than_sources",
            ),
            # Some sources have zero articles
            (
                {"A": 0, "B": 50, "C": 0, "D": 30},
                40,
                {"B": 20, "D": 20},
                "zero_article_sources_ignored",
            ),
        ],
    )
    def test_distribution_scenarios(self, source_counts, limit, expected, test_id):
        """Test various distribution scenarios."""
        result = calculate_quotas(source_counts, limit)

        # Verify total doesn't exceed limit
        assert sum(result.values()) <= limit, f"{test_id}: Total exceeds limit"

        # Verify keys match (excluding zero-count sources)
        expected_keys = set(expected.keys())
        result_keys = set(result.keys())
        assert result_keys == expected_keys, f"{test_id}: Key mismatch"

        # Verify each quota
        for source, quota in expected.items():
            assert result[source] == quota, f"{test_id}: {source} got {result[source]}, expected {quota}"

    def test_fairness_property(self):
        """Verify Max-Min Fairness property: min allocation is maximized."""
        # Scenario: one small source should get its full count before large sources are allocated
        result = calculate_quotas({"small": 5, "large1": 100, "large2": 100}, 50)

        assert result["small"] == 5, "Small source should get full allocation"
        # Remaining 45 split between two large sources
        assert result["large1"] == result["large2"] == 22, "Large sources should split remainder equally"

    def test_zero_limit(self):
        """Zero limit should return zero quotas for all sources."""
        result = calculate_quotas({"A": 100, "B": 50}, 0)
        assert result == {"A": 0, "B": 0}

    def test_empty_sources(self):
        """Empty sources dict should return empty quotas."""
        result = calculate_quotas({}, 50)
        assert result == {}
