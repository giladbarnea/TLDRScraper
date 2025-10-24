/**
 * Summary functionality including effort selection and delivery
 */

import { ARTICLE_STATUS, ClientStorage } from './storage.js';
import {
    markArticleAsRead,
    updateStoredArticleFromCard,
    isCardRemoved,
    toggleCopyButton
} from './article-card.js';

// #region -------[ SummaryEffortSelector ]-------

export const SUMMARY_EFFORT_OPTIONS = [
    { value: 'minimal', label: 'Minimal reasoning' },
    { value: 'low', label: 'Low reasoning' },
    { value: 'medium', label: 'Medium reasoning' },
    { value: 'high', label: 'High reasoning' }
];

export function normalizeSummaryEffort(value) {
    if (typeof value !== 'string') return 'low';
    const normalized = value.trim().toLowerCase();
    return SUMMARY_EFFORT_OPTIONS.some((opt) => opt.value === normalized) ? normalized : 'low';
}

export function getCardSummaryEffort(card) {
    if (!card) return 'low';
    return normalizeSummaryEffort(card.getAttribute('data-summary-effort') || 'low');
}

export function setCardSummaryEffort(card, value) {
    if (!card) return;
    const previousEffort = normalizeSummaryEffort(card.getAttribute('data-summary-effort') || 'low');
    const effort = normalizeSummaryEffort(value);
    if (previousEffort !== effort) {
        card.removeAttribute('data-summary');
        const existingSummary = card.querySelector('.inline-summary');
        if (existingSummary) {
            existingSummary.remove();
        }
        const expandBtnReset = card.querySelector('.expand-btn');
        if (expandBtnReset) {
            expandBtnReset.classList.remove('expanded');
            expandBtnReset.classList.remove('loaded');
            expandBtnReset.classList.add('collapsed-state');
            expandBtnReset.innerHTML = 'Summarize';
            expandBtnReset.title = 'Show summary with default reasoning effort';
        }
        toggleCopyButton(card, false);
    }
    card.setAttribute('data-summary-effort', effort);
    const expandBtn = card.querySelector('.expand-btn');
    if (expandBtn) {
        expandBtn.dataset.summaryEffort = effort;
    }
}

export function setupSummaryEffortControls(card, expandBtn, chevronBtn, dropdown) {
    if (!card || !expandBtn || !chevronBtn || !dropdown) return;

    function hideDropdown() {
        dropdown.classList.remove('visible');
        chevronBtn.classList.remove('active');
    }

    function showDropdown() {
        dropdown.classList.add('visible');
        chevronBtn.classList.add('active');
    }

    function toggleDropdown(event) {
        event.preventDefault();
        event.stopPropagation();

        if (dropdown.classList.contains('visible')) {
            hideDropdown();
        } else {
            showDropdown();
        }
    }

    chevronBtn.addEventListener('click', toggleDropdown);

    document.addEventListener('click', function(event) {
        if (!dropdown.contains(event.target) &&
            !chevronBtn.contains(event.target) &&
            dropdown.classList.contains('visible')) {
            hideDropdown();
        }
    });

    dropdown.querySelectorAll('.effort-dropdown-item').forEach(item => {
        item.addEventListener('click', async function(event) {
            event.preventDefault();
            event.stopPropagation();

            const effort = this.getAttribute('data-effort');
            setCardSummaryEffort(card, effort);
            hideDropdown();

            expandBtn.click();
        });
    });

    hideDropdown();
}

// #endregion

// #region -------[ SummaryDelivery ]-------

export function bindSummaryExpansion() {
    document.addEventListener('click', async function(e) {
        const expandBtn = e.target.closest('.expand-btn:not(.expand-chevron-btn)');
        const link = e.target.closest('.article-link');

        if (e.target.closest('.expand-chevron-btn') || e.target.closest('.effort-dropdown-item')) {
            return;
        }

        if (!expandBtn && !link) return;

        const target = expandBtn || link;
        const card = target.closest('.article-card');
        if (!card || isCardRemoved(card)) return;

        if (link && !card.contains(link)) return;

        const url = target.getAttribute('data-url') || target.getAttribute('href');
        if (!url || url.startsWith('#')) return;

        if (link && (e.ctrlKey || e.metaKey)) {
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        const btn = card.querySelector('.expand-btn');
        const summaryEffort = getCardSummaryEffort(card);

        let expander = card.querySelector('.inline-summary');
        if (expander) {
            if (expander.style.display === 'none') {
                expander.style.display = 'block';
                if (btn) {
                    btn.innerHTML = 'Hide';
                    btn.title = 'Hide summary';
                    btn.classList.add('expanded');
                    btn.classList.remove('collapsed-state');
                }
                toggleCopyButton(card, true);
            } else {
                expander.style.display = 'none';
                if (btn) {
                    const isLoaded = btn.classList.contains('loaded');
                    btn.innerHTML = isLoaded ? 'Available' : 'Summarize';
                    btn.title = isLoaded ? 'Summary cached - click to show' : 'Show summary with default reasoning effort';
                    btn.classList.remove('expanded');
                    if (!isLoaded) {
                        btn.classList.add('collapsed-state');
                    }
                }
                toggleCopyButton(card, false);
                markArticleAsRead(card);
            }
            return;
        }

        const loadedSummary = card.getAttribute('data-summary');

        if (loadedSummary) {
            expander = document.createElement('div');
            expander.className = 'inline-summary';
            const html = DOMPurify.sanitize(marked.parse(loadedSummary));
            expander.innerHTML = '<strong>Summary</strong>' + html;
            expander.querySelectorAll('a[href]').forEach(function(a) {
                a.setAttribute('target', '_blank');
                a.setAttribute('rel', 'noopener noreferrer');
                a.classList.remove('article-link');
            });
            card.appendChild(expander);

            if (btn) {
                btn.innerHTML = 'Hide';
                btn.title = 'Hide summary';
                btn.classList.add('expanded');
                btn.classList.remove('collapsed-state');
                btn.classList.add('loaded');
            }
            updateStoredArticleFromCard(card, article => ({
                ...article,
                summary: {
                    status: ARTICLE_STATUS.available,
                    markdown: loadedSummary,
                    effort: summaryEffort,
                    checkedAt: new Date().toISOString(),
                    errorMessage: null
                }
            }));
            toggleCopyButton(card, true);
            return;
        }

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = 'Loading...';
            btn.title = 'Loading summary...';
        }

        expander = document.createElement('div');
        expander.className = 'inline-summary';
        expander.textContent = 'Summarizing...';
        card.appendChild(expander);
        updateStoredArticleFromCard(card, article => ({
            ...article,
            summary: {
                status: ARTICLE_STATUS.creating,
                markdown: '',
                effort: summaryEffort,
                checkedAt: new Date().toISOString(),
                errorMessage: null
            }
        }));

        try {
            const resp = await fetch('/api/summarize-url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, summary_effort: summaryEffort })
            });
            const data = await resp.json();
            if (data.success) {
                if (getCardSummaryEffort(card) !== summaryEffort) {
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = 'Summarize';
                        btn.title = 'Show summary with default reasoning effort';
                        btn.classList.add('collapsed-state');
                    }
                    if (expander && expander.parentNode) {
                        expander.remove();
                    }
                    toggleCopyButton(card, false);
                    return;
                }
                const html = DOMPurify.sanitize(marked.parse(data.summary_markdown || ''));
                expander.innerHTML = '<strong>Summary</strong>' + html;
                expander.querySelectorAll('a[href]').forEach(function(a) {
                    a.setAttribute('target', '_blank');
                    a.setAttribute('rel', 'noopener noreferrer');
                    a.classList.remove('article-link');
                });

                card.setAttribute('data-summary', data.summary_markdown || '');
                updateStoredArticleFromCard(card, article => ({
                    ...article,
                    summary: {
                        status: ARTICLE_STATUS.available,
                        markdown: data.summary_markdown || '',
                        effort: summaryEffort,
                        checkedAt: new Date().toISOString(),
                        errorMessage: null
                    }
                }));

                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = 'Hide';
                    btn.title = 'Hide summary';
                    btn.classList.add('expanded');
                    btn.classList.remove('collapsed-state');
                    btn.classList.add('loaded');
                }
                toggleCopyButton(card, true);
            } else {
                expander.classList.add('error');
                expander.textContent = 'Error: ' + (data.error || 'Failed to summarize');

                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = 'Summarize';
                    btn.title = 'Show summary with default reasoning effort';
                    btn.classList.add('collapsed-state');
                }
                toggleCopyButton(card, false);
                updateStoredArticleFromCard(card, article => ({
                    ...article,
                    summary: {
                        status: ARTICLE_STATUS.error,
                        markdown: '',
                        effort: summaryEffort,
                        checkedAt: new Date().toISOString(),
                        errorMessage: data.error || 'Failed to summarize'
                    }
                }));
            }
        } catch (err) {
            expander.classList.add('error');
            expander.textContent = 'Network error: ' + (err?.message || String(err));

            if (btn) {
                btn.disabled = false;
                btn.innerHTML = 'Summarize';
                btn.title = 'Show summary with default reasoning effort';
                btn.classList.add('collapsed-state');
            }
            toggleCopyButton(card, false);
            updateStoredArticleFromCard(card, article => ({
                ...article,
                summary: {
                    status: ARTICLE_STATUS.error,
                    markdown: '',
                    effort: summaryEffort,
                    checkedAt: new Date().toISOString(),
                    errorMessage: err?.message || 'Failed to summarize'
                }
            }));
        }
    }, true);
}

// #endregion
