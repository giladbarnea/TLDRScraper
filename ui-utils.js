/**
 * General UI utilities and helpers
 */

import { isCardRemoved, setCardRemovedState, updateStoredArticleFromCard } from './article-card.js';
import { reapplyArticleState } from './dom-builder.js';

// #region -------[ SummaryClipboard ]-------

export const clipboardIconMarkup = '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';

let copyToastTimeout;

export function showCopyToast() {
    const copyToast = document.getElementById('copyToast');
    if (!copyToast) return;
    clearTimeout(copyToastTimeout);
    copyToast.classList.add('show');
    copyToastTimeout = setTimeout(function() {
        copyToast.classList.remove('show');
    }, 2000);
}

export function bindCopySummaryFlow() {
    document.addEventListener('click', async function(e) {
        const btn = e.target.closest('.copy-summary-btn');
        if (!btn) return;

        e.preventDefault();
        e.stopPropagation();

        const card = btn.closest('.article-card');
        if (!card || isCardRemoved(card)) return;

        const payload = `---\ntitle: ${card.getAttribute('data-title')}\nurl: ${card.getAttribute('data-url')}\n---\n${card.getAttribute('data-summary')}`;
        await navigator.clipboard.writeText(payload);
        showCopyToast();
    }, true);
}

// #endregion

// #region -------[ RemovalControls ]-------

export function bindRemovalControls() {
    document.addEventListener('click', function(e) {
        const removeBtn = e.target.closest('.remove-article-btn');
        if (!removeBtn) return;

        e.preventDefault();
        e.stopPropagation();

        const card = removeBtn.closest('.article-card');
        if (!card) return;

        const nextState = !isCardRemoved(card);

        // Update storage FIRST, then UI
        updateStoredArticleFromCard(card, article => ({
            ...article,
            removed: nextState
        }));

        // Re-sync state from cache to ensure consistency
        const date = card.getAttribute('data-date');
        const url = card.getAttribute('data-url');
        if (date && url) reapplyArticleState(date, url);

        setCardRemovedState(card, nextState);
    });
}

// #endregion
