import json

from adapters.trendshift_adapter import _extract_repositories_from_html


def _ld_json_html(items: list[dict]) -> str:
    payload = {"@type": "ItemList", "itemListElement": [{"item": item} for item in items]}
    return f'<script type="application/ld+json">{json.dumps(payload)}</script>'


def test_extract_repositories_from_html_parses_item():
    html = _ld_json_html(
        [
            {
                "name": "owner/repo",
                "description": "A cool project",
                "codeRepository": "https://github.com/owner/repo",
            }
        ]
    )
    repos = _extract_repositories_from_html(html)
    assert len(repos) == 1
    assert repos[0]["name"] == "owner/repo"
    assert repos[0]["url"] == "https://github.com/owner/repo"
    assert repos[0]["description"] == "A cool project"


def test_extract_repositories_deduplicates_by_url():
    html = _ld_json_html(
        [
            {"name": "owner/repo", "description": "First", "codeRepository": "https://github.com/owner/repo"},
            {"name": "owner/repo", "description": "Duplicate", "codeRepository": "https://github.com/owner/repo"},
        ]
    )
    repos = _extract_repositories_from_html(html)
    assert len(repos) == 1


def test_extract_repositories_strips_description_whitespace():
    html = _ld_json_html(
        [{"name": "owner/repo", "description": "Trailing space. ", "codeRepository": "https://github.com/owner/repo"}]
    )
    repos = _extract_repositories_from_html(html)
    assert repos[0]["description"] == "Trailing space."
