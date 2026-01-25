import util


def test_should_rescrape_respects_pacific_midnight_boundary():
    date_str = "2025-01-23"
    assert util.should_rescrape(date_str, "2025-01-24T07:59:59Z") is True
    assert util.should_rescrape(date_str, "2025-01-24T08:00:00Z") is False


def test_should_rescrape_handles_dst_transition():
    date_str = "2025-03-09"
    assert util.should_rescrape(date_str, "2025-03-10T06:59:59Z") is True
    assert util.should_rescrape(date_str, "2025-03-10T07:00:00Z") is False
