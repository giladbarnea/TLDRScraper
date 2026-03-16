from adapters.trendshift_adapter import _extract_repositories_from_html, _extract_repo_name
from bs4 import BeautifulSoup


def test_extract_repositories_from_html_parses_card():
    html = """
    <div class="rounded-lg border border-gray-300 bg-white">
        <a href="/repositories/123">owner/repo</a>
        <a href="https://github.com/owner/repo">GitHub</a>
        <div class="text-gray-500 text-xs leading-5">A cool project</div>
    </div>
    """
    repos = _extract_repositories_from_html(html)
    assert len(repos) == 1
    assert repos[0]["name"] == "owner/repo"
    assert repos[0]["url"] == "https://github.com/owner/repo"
    assert repos[0]["description"] == "A cool project"


def test_extract_repositories_deduplicates_by_url():
    html = """
    <div class="rounded-lg border border-gray-300 bg-white">
        <a href="/repositories/1">owner/repo</a>
        <div class="text-gray-500 text-xs leading-5">First</div>
    </div>
    <div class="rounded-lg border border-gray-300 bg-white">
        <a href="/repositories/2">owner/repo</a>
        <div class="text-gray-500 text-xs leading-5">Duplicate</div>
    </div>
    """
    repos = _extract_repositories_from_html(html)
    assert len(repos) == 1


def test_extract_repo_name_from_internal_link():
    html = '<div><a href="/repositories/123">acme/widget</a></div>'
    card = BeautifulSoup(html, "html.parser").div
    assert _extract_repo_name(card) == "acme/widget"


def test_extract_repo_name_from_github_link_fallback():
    html = '<div><a href="https://github.com/acme/widget">GitHub</a></div>'
    card = BeautifulSoup(html, "html.parser").div
    assert _extract_repo_name(card) == "acme/widget"


def test_extract_repo_name_returns_none_for_empty_card():
    html = "<div><span>No links here</span></div>"
    card = BeautifulSoup(html, "html.parser").div
    assert _extract_repo_name(card) is None
