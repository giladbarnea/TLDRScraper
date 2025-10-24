/**
 * TldrDelivery handles TLDR retrieval from the /api/tldr-url endpoint.
 */

import { ARTICLE_STATUS } from './storage.js';
import {
    markArticleAsRead,
    updateStoredArticleFromCard,
    isCardRemoved
} from './article-card.js';
import { getCardSummaryEffort } from './summary.js';

// #region -------[ TldrDelivery ]-------

export function bindTldrExpansion() {
    document.addEventListener('click', async function(e) {
        const tldrBtn = e.target.closest('.tldr-btn');
        if (!tldrBtn) return;

        e.preventDefault();
        e.stopPropagation();

        const card = tldrBtn.closest('.article-card');
        if (!card || isCardRemoved(card)) return;

        const url = tldrBtn.getAttribute('data-url');
        if (!url) return;

        const summaryEffort = getCardSummaryEffort(card);

        let expander = card.querySelector('.inline-tldr');
        if (expander) {
            if (expander.style.display === 'none') {
                expander.style.display = 'block';
                tldrBtn.innerHTML = 'Hide';
                tldrBtn.title = 'Hide TLDR';
                tldrBtn.classList.add('expanded');
                tldrBtn.classList.remove('collapsed-state');
            } else {
                expander.style.display = 'none';
                const isLoaded = tldrBtn.classList.contains('loaded');
                tldrBtn.innerHTML = isLoaded ? 'Available' : 'TLDR';
                tldrBtn.title = isLoaded ? 'TLDR cached - click to show' : 'Show TLDR';
                tldrBtn.classList.remove('expanded');
                if (!isLoaded) {
                    tldrBtn.classList.add('collapsed-state');
                }
                markArticleAsRead(card);
            }
            return;
        }

        const loadedTldr = card.getAttribute('data-tldr');

        if (loadedTldr) {
            expander = document.createElement('div');
            expander.className = 'inline-tldr';
            const html = DOMPurify.sanitize(marked.parse(loadedTldr));
            expander.innerHTML = '<strong>TLDR</strong>' + html;
            expander.querySelectorAll('a[href]').forEach(function(a) {
                a.setAttribute('target', '_blank');
                a.setAttribute('rel', 'noopener noreferrer');
                a.classList.remove('article-link');
            });
            card.appendChild(expander);

            tldrBtn.innerHTML = 'Hide';
            tldrBtn.title = 'Hide TLDR';
            tldrBtn.classList.add('expanded');
            tldrBtn.classList.remove('collapsed-state');
            tldrBtn.classList.add('loaded');
            updateStoredArticleFromCard(card, article => ({
                ...article,
                tldr: {
                    status: ARTICLE_STATUS.available,
                    markdown: loadedTldr,
                    effort: summaryEffort,
                    checkedAt: new Date().toISOString(),
                    errorMessage: null
                }
            }));
            return;
        }

        tldrBtn.disabled = true;
        tldrBtn.innerHTML = 'Loading...';
        tldrBtn.title = 'Loading TLDR...';

        expander = document.createElement('div');
        expander.className = 'inline-tldr';
        expander.textContent = 'Creating TLDR...';
        card.appendChild(expander);
        updateStoredArticleFromCard(card, article => ({
            ...article,
            tldr: {
                status: ARTICLE_STATUS.creating,
                markdown: '',
                effort: summaryEffort,
                checkedAt: new Date().toISOString(),
                errorMessage: null
            }
        }));

        try {
            const resp = await fetch('/api/tldr-url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, summary_effort: summaryEffort })
            });
            const data = await resp.json();
            if (data.success) {
                if (getCardSummaryEffort(card) !== summaryEffort) {
                    tldrBtn.disabled = false;
                    tldrBtn.innerHTML = 'TLDR';
                    tldrBtn.title = 'Show TLDR';
                    tldrBtn.classList.add('collapsed-state');
                    if (expander && expander.parentNode) {
                        expander.remove();
                    }
                    return;
                }
                const html = DOMPurify.sanitize(marked.parse(data.tldr_markdown || ''));
                expander.innerHTML = '<strong>TLDR</strong>' + html;
                expander.querySelectorAll('a[href]').forEach(function(a) {
                    a.setAttribute('target', '_blank');
                    a.setAttribute('rel', 'noopener noreferrer');
                    a.classList.remove('article-link');
                });

                card.setAttribute('data-tldr', data.tldr_markdown || '');
                updateStoredArticleFromCard(card, article => ({
                    ...article,
                    tldr: {
                        status: ARTICLE_STATUS.available,
                        markdown: data.tldr_markdown || '',
                        effort: summaryEffort,
                        checkedAt: new Date().toISOString(),
                        errorMessage: null
                    }
                }));

                tldrBtn.disabled = false;
                tldrBtn.innerHTML = 'Hide';
                tldrBtn.title = 'Hide TLDR';
                tldrBtn.classList.add('expanded');
                tldrBtn.classList.remove('collapsed-state');
                tldrBtn.classList.add('loaded');
            } else {
                expander.classList.add('error');
                expander.textContent = 'Error: ' + (data.error || 'Failed to create TLDR');

                tldrBtn.disabled = false;
                tldrBtn.innerHTML = 'TLDR';
                tldrBtn.title = 'Show TLDR';
                tldrBtn.classList.add('collapsed-state');
                updateStoredArticleFromCard(card, article => ({
                    ...article,
                    tldr: {
                        status: ARTICLE_STATUS.error,
                        markdown: '',
                        effort: summaryEffort,
                        checkedAt: new Date().toISOString(),
                        errorMessage: data.error || 'Failed to create TLDR'
                    }
                }));
            }
        } catch (err) {
            expander.classList.add('error');
            expander.textContent = 'Network error: ' + (err?.message || String(err));

            tldrBtn.disabled = false;
            tldrBtn.innerHTML = 'TLDR';
            tldrBtn.title = 'Show TLDR';
            tldrBtn.classList.add('collapsed-state');
            updateStoredArticleFromCard(card, article => ({
                ...article,
                tldr: {
                    status: ARTICLE_STATUS.error,
                    markdown: '',
                    effort: summaryEffort,
                    checkedAt: new Date().toISOString(),
                    errorMessage: err?.message || String(err)
                }
            }));
        }
    }, true);
}

// #endregion
