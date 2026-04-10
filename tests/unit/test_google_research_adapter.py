from adapters.google_research_adapter import GoogleResearchAdapter
from bs4 import BeautifulSoup

from newsletter_config import NEWSLETTER_CONFIGS


def _build_card_html(title: str, date_text: str, href: str, tags: list[str]) -> str:
    tag_items = "".join(
        f"""
        <li class="glue-card__link-list__item">
            <span class="not-glue caption">{tag}</span>
        </li>
        """
        for tag in tags
    )
    return f"""
    <a class="glue-card not-glue" href="{href}">
        <div class="glue-card__content --no-media">
            <p class="glue-label glue-spacer-1-bottom">{date_text}</p>
            <span class="headline-5 js-gt-item-id">{title}</span>
        </div>
        <ul class="glue-card__link-list">
            {tag_items}
        </ul>
    </a>
    """


def _build_archive_page_html(cards: str, total_pages: int | None = None) -> str:
    pagination_html = ""
    if total_pages is not None:
        pagination_html = f"""
        <div class="blog-list-base__pagination" data-hot-swap="pagination">
            <form class="pagination__form" data-max-pages="{total_pages}">
                <input class="js-pagination-input" value="1" />
                <label>of {total_pages} pages</label>
            </form>
        </div>
        """

    return f"""
    <html>
      <body>
        <div class="featured-post">
          {_build_card_html(
              title="Featured duplicate that should be ignored",
              date_text="April 9, 2026",
              href="/blog/featured-duplicate/",
              tags=["Featured"],
          )}
        </div>
        <div class="search-wrapper">
          <input type="search" placeholder="Search" />
        </div>
        <section class="blog-posts-grid glue-grid">
          <div class="glue-grid__col">
            <ul class="glue-grid blog-posts-grid__cards">
              <li class="glue-grid__col">
                {cards}
              </li>
            </ul>
          </div>
        </section>
        {pagination_html}
      </body>
    </html>
    """


def test_extract_article_cards_reads_only_archive_grid():
    adapter = GoogleResearchAdapter(NEWSLETTER_CONFIGS["google_research"])
    html = _build_archive_page_html(
        cards="".join(
            [
                _build_card_html(
                    title="ConvApparel: Measuring and bridging the realism gap in user simulators",
                    date_text="April 9, 2026",
                    href="/blog/convapparel-measuring-and-bridging-the-realism-gap-in-user-simulators/",
                    tags=["Generative AI", "Machine Intelligence"],
                ),
                _build_card_html(
                    title="Improving the academic workflow: Introducing two AI agents for better figures and peer review",
                    date_text="April 8, 2026",
                    href="/blog/improving-the-academic-workflow-introducing-two-ai-agents-for-better-figures-and-peer-review/",
                    tags=["Generative AI", "Natural Language Processing"],
                ),
            ]
        ),
        total_pages=1,
    )

    soup = BeautifulSoup(html, "html.parser")
    cards = adapter._extract_article_cards(soup)
    titles = [card.select_one(".headline-5").get_text(" ", strip=True) for card in cards]

    assert len(cards) == 2, f"Expected only the two archive-grid cards. Got {len(cards)} cards."
    assert titles == [
        "ConvApparel: Measuring and bridging the realism gap in user simulators",
        "Improving the academic workflow: Introducing two AI agents for better figures and peer review",
    ], f"Expected archive-grid titles only. Got {titles=!r}"


def test_scrape_date_collects_exact_date_from_paginated_archive(monkeypatch):
    adapter = GoogleResearchAdapter(NEWSLETTER_CONFIGS["google_research"])
    page_one_html = _build_archive_page_html(
        cards=_build_card_html(
            title="Protecting cities with AI-driven flash flood forecasting",
            date_text="March 12, 2026",
            href="/blog/protecting-cities-with-ai-driven-flash-flood-forecasting/",
            tags=["Climate & Sustainability", "Earth AI"],
        ),
        total_pages=2,
    )
    page_two_html = _build_archive_page_html(
        cards=_build_card_html(
            title="A March 6 post",
            date_text="March 6, 2026",
            href="/blog/a-march-6-post/",
            tags=["Generative AI", "Natural Language Processing"],
        ),
        total_pages=2,
    )

    def fake_fetch_archive_page(archive_url: str) -> str:
        if archive_url.endswith("/2026/03"):
            return page_one_html
        if archive_url.endswith("/2026/03?page=2"):
            return page_two_html
        raise AssertionError(f"Unexpected archive URL: {archive_url}")

    monkeypatch.setattr(adapter, "_fetch_archive_page", fake_fetch_archive_page)

    result = adapter.scrape_date("2026-03-06", excluded_urls=[])
    articles = result["articles"]

    assert len(articles) == 1, f"Expected one exact-date article from page 2. Got {articles=!r}"
    assert articles[0]["title"] == "A March 6 post", (
        f"Expected the March 6 card to be returned. Got {articles[0]['title']=!r}"
    )
    assert articles[0]["url"] == "research.google/blog/a-march-6-post", (
        f"Expected canonicalized article URL. Got {articles[0]['url']=!r}"
    )
    assert articles[0]["article_meta"] == "Generative AI · Natural Language Processing", (
        f"Expected tags joined into article_meta. Got {articles[0]['article_meta']=!r}"
    )
    assert result["issues"] == [
        {
            "date": "2026-03-06",
            "source_id": "google_research",
            "category": "Google Research Blog",
            "title": None,
            "subtitle": None,
        }
    ], f"Expected a single issue entry for the scrape date. Got {result['issues']=!r}"
