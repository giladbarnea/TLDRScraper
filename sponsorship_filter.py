def is_sponsored_section(text):
    """Check if a section header indicates sponsored content"""
    sponsored_indicators = [
        "sponsor",
        "sponsored",
        "advertisement",
        "advertise",
        "partner",
        "tldr deals",
        "deals",
        "promo",
        "promotion",
    ]
    return any(indicator in text.lower() for indicator in sponsored_indicators)


def is_sponsored_link(title, url):
    """Check if a link appears to be sponsored content"""
    sponsored_keywords = [
        "sponsor",
        "sponsored",
        "advertisement",
        "advertise",
        "partner content",
        "affiliate",
        "promo",
        "promotion",
    ]

    title_lower = title.lower()
    return any(keyword in title_lower for keyword in sponsored_keywords)


def is_sponsored_url(url: str) -> bool:
    """Detect sponsored content based ONLY on bulletproof UTM parameter combinations.

    This function only uses explicit, unambiguous UTM indicators that definitively
    signal paid/sponsored placement. Title-based filtering (is_sponsored_link) handles
    the rest via "(Sponsor)" markers in article titles.

    Bulletproof rules:
    - utm_medium contains explicit paid/sponsored terms (thirdparty_advertising, paid, sponsor, etc.)
    - utm_content or utm_term explicitly says "paid"
    """
    try:
        import urllib.parse as urlparse

        parsed = urlparse.urlparse(url)
        query_params = {
            k.lower(): v for k, v in urlparse.parse_qs(parsed.query).items()
        }

        medium_values = [v.lower() for v in query_params.get("utm_medium", [])]
        medium_str = " ".join(medium_values)

        explicit_paid_mediums = [
            "thirdparty_advertising",
            "paid",
            "sponsor",
            "sponsored",
            "cpc",
            "cpm",
        ]

        if any(indicator in medium_str for indicator in explicit_paid_mediums):
            return True

        content_values = [v.lower() for v in query_params.get("utm_content", [])]
        term_values = [v.lower() for v in query_params.get("utm_term", [])]

        if "paid" in " ".join(content_values) or "paid" in " ".join(term_values):
            return True

        return False
    except Exception:
        return False
