/**
 * ArticleStateTracks keeps article cards ordered by unread and read outcomes for every downstream flow.
 */

import { ClientStorage } from './storage.js';

// #region -------[ ArticleStateTracks ]-------

export function getArticleState(card) {
    if (card.getAttribute('data-removed') === 'true') return 2;
    if (card.classList.contains('read')) return 1;
    return 0;
}

export function sortArticlesByState(articleList) {
    const sectionTitles = Array.from(articleList.querySelectorAll('.section-title'));
    sectionTitles.forEach(section => section.remove());

    const cards = Array.from(articleList.querySelectorAll('.article-card'));
    cards.sort((a, b) => {
        const stateDiff = getArticleState(a) - getArticleState(b);
        if (stateDiff !== 0) return stateDiff;
        const orderA = Number(a.getAttribute('data-original-order')) || 0;
        const orderB = Number(b.getAttribute('data-original-order')) || 0;
        return orderA - orderB;
    });

    let lastSectionKey = null;
    cards.forEach((card, index) => {
        const sectionTitle = card.getAttribute('data-section-title');
        const sectionEmoji = card.getAttribute('data-section-emoji');
        const sectionOrder = card.getAttribute('data-section-order') || '';

        const sectionKey = sectionTitle ? `${sectionOrder}__${sectionTitle}` : null;

        if (sectionKey && sectionKey !== lastSectionKey) {
            const labelParts = [];
            if (sectionEmoji) {
                labelParts.push(sectionEmoji);
            }
            if (sectionTitle) {
                labelParts.push(sectionTitle);
            }
            const sectionLabel = labelParts.join(' ').trim();
            if (sectionLabel) {
                const sectionEl = document.createElement('div');
                sectionEl.className = 'section-title';
                sectionEl.textContent = sectionLabel;
                articleList.appendChild(sectionEl);
            }
            lastSectionKey = sectionKey;
        } else if (!sectionTitle && lastSectionKey !== null) {
            lastSectionKey = null;
        }

        articleList.appendChild(card);
        const number = card.querySelector('.article-number');
        if (number) number.textContent = index + 1;
    });
    markCategoryBoundaries(articleList);
}

export function markCategoryBoundaries(articleList) {
    const cards = Array.from(articleList.querySelectorAll('.article-card'));
    let lastState = -1;
    cards.forEach(card => {
        const state = getArticleState(card);
        card.classList.remove('category-first');
        if (state !== lastState && lastState !== -1) {
            card.classList.add('category-first');
        }
        lastState = state;
    });
}

export function parseTitleWithDomain(titleWithDomain) {
    if (typeof titleWithDomain !== 'string') {
        return { title: '', domain: '' };
    }

    const match = titleWithDomain.match(/\s*\(([^()]*)\)\s*$/);
    if (!match) {
        return { title: titleWithDomain.trim(), domain: '' };
    }

    const domain = match[1].trim();
    const title = titleWithDomain
        .slice(0, titleWithDomain.length - match[0].length)
        .trim();
    return { title, domain };
}

export function getDomainLabelFromUrl(url) {
    if (typeof url !== 'string' || !url) {
        return '';
    }

    try {
        const parsed = new URL(url);
        let hostname = (parsed.hostname || '').toLowerCase();
        if (hostname.startsWith('www.')) {
            hostname = hostname.slice(4);
        }

        const parts = hostname.split('.');
        if (parts.length >= 2) {
            const main = parts[parts.length - 2];
            if (main) {
                return main.charAt(0).toUpperCase() + main.slice(1);
            }
        } else if (hostname) {
            return hostname.charAt(0).toUpperCase() + hostname.slice(1);
        }
    } catch (err) {
        return '';
    }

    return '';
}

export function setArticleLinkText(link, text) {
    if (!link) return;
    let textSpan = link.querySelector('.article-link-text');
    if (!textSpan) {
        textSpan = document.createElement('span');
        textSpan.className = 'article-link-text';
        link.appendChild(textSpan);
    }
    textSpan.textContent = text || '';
}

export function isCardRemoved(card) {
    if (!card) return false;
    return card.getAttribute('data-removed') === 'true';
}

export function setCardRemovedState(card, removed) {
    if (!card) return;

    const isRemoved = Boolean(removed);
    card.setAttribute('data-removed', isRemoved ? 'true' : 'false');
    card.classList.toggle('removed', isRemoved);

    const articleList = card.closest('.article-list');

    const removeBtn = card.querySelector('.remove-article-btn');
    if (removeBtn) {
        removeBtn.innerHTML = isRemoved ? 'Restore' : 'Remove';
        removeBtn.title = isRemoved
            ? 'Restore this article to the list'
            : 'Remove this article from the list';
    }

    const link = card.querySelector('.article-link');
    if (link) {
        if (isRemoved) {
            link.setAttribute('tabindex', '-1');
        } else {
            link.removeAttribute('tabindex');
        }
    }

    if (isRemoved) {
        const summaryExpander = card.querySelector('.inline-summary');
        if (summaryExpander) summaryExpander.remove();

        const tldrExpander = card.querySelector('.inline-tldr');
        if (tldrExpander) tldrExpander.remove();

        const expandBtn = card.querySelector('.expand-btn');
        if (expandBtn) {
            expandBtn.classList.remove('expanded');
            const loaded = expandBtn.classList.contains('loaded');
            expandBtn.innerHTML = loaded ? 'Available' : 'Summarize';
            expandBtn.title = loaded
                ? 'Summary cached - click to show'
                : 'Show summary with default reasoning effort';
        }

        const tldrBtn = card.querySelector('.tldr-btn');
        if (tldrBtn) {
            tldrBtn.classList.remove('expanded');
            const loaded = tldrBtn.classList.contains('loaded');
            tldrBtn.innerHTML = loaded ? 'Available' : 'TLDR';
            tldrBtn.title = loaded
                ? 'TLDR cached - click to show'
                : 'Show TLDR';
        }

        toggleCopyButton(card, false);
        if (articleList) sortArticlesByState(articleList);
        return;
    }

    const hasSummary = Boolean(card.getAttribute('data-summary'));
    toggleCopyButton(card, hasSummary);
    if (articleList) sortArticlesByState(articleList);
}

export function markArticleAsRead(card) {
    card.classList.remove('unread');
    card.classList.add('read');
    const articleList = card.closest('.article-list');
    if (articleList) sortArticlesByState(articleList);
    updateStoredArticleFromCard(card, article => ({
        ...article,
        read: {
            isRead: true,
            markedAt: new Date().toISOString()
        }
    }));
}

export function updateStoredArticleFromCard(card, updater) {
    if (!card) return;
    const date = card.getAttribute('data-date');
    const url = card.getAttribute('data-url');
    if (!date || !url) return;
    ClientStorage.updateArticle(date, url, updater);
}

export function toggleCopyButton(card, shouldShow) {
    const copyBtn = card.querySelector('.copy-summary-btn');
    if (!copyBtn) return;
    if (shouldShow) {
        copyBtn.classList.add('visible');
        return;
    }
    copyBtn.classList.remove('visible');
}

// #endregion
