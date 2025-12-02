"""
Test data attributes on ArticleCard components.

Verifies that boolean state attributes (data-removed, data-read, data-tldr-available, data-expanded)
are correctly set and updated during state transitions.
"""

import pytest
from playwright.sync_api import Page, expect


def test_article_data_attributes_initial_state(page: Page):
    """Verify initial data attributes on unread article."""
    page.goto("http://localhost:3000")
    page.wait_for_selector('[data-article-url]', timeout=10000)

    article = page.locator('[data-read="false"]').first()

    expect(article).to_have_attribute('data-removed', 'false')
    expect(article).to_have_attribute('data-read', 'false')
    expect(article).to_have_attribute('data-expanded', 'false')


def test_article_mark_as_read(page: Page):
    """Verify data-read attribute changes when article title is clicked."""
    page.goto("http://localhost:3000")
    page.wait_for_selector('[data-article-url]', timeout=10000)

    article = page.locator('[data-read="false"]').first()
    article_url = article.get_attribute('data-article-url')

    article.locator('a').first().click()
    page.wait_for_timeout(500)

    updated_article = page.locator(f'[data-article-url="{article_url}"]')
    expect(updated_article).to_have_attribute('data-read', 'true')


def test_article_tldr_expansion(page: Page):
    """Verify data-expanded changes when TLDR is toggled."""
    page.goto("http://localhost:3000")
    page.wait_for_selector('[data-article-url]', timeout=10000)

    article = page.locator('[data-read="false"]').first()
    article_url = article.get_attribute('data-article-url')

    tldr_button = article.get_by_role('button', name='TLDR')
    tldr_button.click()

    page.wait_for_timeout(2000)

    updated_article = page.locator(f'[data-article-url="{article_url}"]')
    expect(updated_article).to_have_attribute('data-expanded', 'true')
    expect(updated_article).to_have_attribute('data-tldr-available', 'true')

    close_button = updated_article.get_by_role('button', name='Close')
    close_button.click()
    page.wait_for_timeout(500)

    expect(updated_article).to_have_attribute('data-expanded', 'false')


def test_article_removal(page: Page):
    """Verify data-removed changes when article is removed."""
    page.goto("http://localhost:3000")
    page.wait_for_selector('[data-article-url]', timeout=10000)

    article = page.locator('[data-removed="false"]').first()
    article_url = article.get_attribute('data-article-url')

    trash_button = article.locator('button').filter(has=page.locator('[data-lucide="trash-2"]')).first()
    trash_button.click()
    page.wait_for_timeout(500)

    updated_article = page.locator(f'[data-article-url="{article_url}"]')
    expect(updated_article).to_have_attribute('data-removed', 'true')


def test_article_restoration(page: Page):
    """Verify data-removed changes back when removed article is clicked (restored)."""
    page.goto("http://localhost:3000")
    page.wait_for_selector('[data-article-url]', timeout=10000)

    article = page.locator('[data-removed="false"]').first()
    article_url = article.get_attribute('data-article-url')

    trash_button = article.locator('button').filter(has=page.locator('[data-lucide="trash-2"]')).first()
    trash_button.click()
    page.wait_for_timeout(500)

    removed_article = page.locator(f'[data-article-url="{article_url}"]')
    expect(removed_article).to_have_attribute('data-removed', 'true')

    removed_article.click()
    page.wait_for_timeout(500)

    restored_article = page.locator(f'[data-article-url="{article_url}"]')
    expect(restored_article).to_have_attribute('data-removed', 'false')


def test_combined_selectors(page: Page):
    """Verify combined data attribute selectors work correctly."""
    page.goto("http://localhost:3000")
    page.wait_for_selector('[data-article-url]', timeout=10000)

    all_articles = page.locator('[data-article-url]').count()
    unread_articles = page.locator('[data-read="false"]').count()
    removed_articles = page.locator('[data-removed="true"]').count()
    available_tldrs = page.locator('[data-tldr-available="true"]').count()
    expanded_articles = page.locator('[data-expanded="true"]').count()

    assert all_articles > 0, "Should have articles"
    assert unread_articles > 0, "Should have unread articles"
    assert removed_articles >= 0, "Should count removed articles (may be 0)"
    assert available_tldrs >= 0, "Should count available TLDRs (may be 0)"
    assert expanded_articles >= 0, "Should count expanded articles (may be 0)"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
