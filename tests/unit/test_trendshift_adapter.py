from adapters.trendshift_adapter import _build_calendar_aria_label
from adapters.trendshift_adapter import _extract_description_line
from adapters.trendshift_adapter import _ordinal_suffix


def test_build_calendar_aria_label_for_requested_dates():
    assert _build_calendar_aria_label("2026-03-05") == "Thursday, March 5th, 2026"
    assert _build_calendar_aria_label("2026-03-02") == "Monday, March 2nd, 2026"


def test_ordinal_suffix_handles_teen_exception():
    assert _ordinal_suffix(11) == "th"
    assert _ordinal_suffix(12) == "th"
    assert _ordinal_suffix(13) == "th"
    assert _ordinal_suffix(21) == "st"


def test_extract_description_line_prefers_last_non_metric_line():
    lines = ["1", "paperclipai/paperclip", "TypeScript", "9.5k", "1.1k", "GitHub", "Open-source orchestration"]
    assert _extract_description_line(lines) == "Open-source orchestration"
    assert _extract_description_line(lines[:-1]) == ""
