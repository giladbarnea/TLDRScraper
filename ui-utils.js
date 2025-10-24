/**
 * General UI utilities and helpers
 */

import { isCardRemoved, setCardRemovedState, updateStoredArticleFromCard } from './article-card.js';

// #region -------[ DebugPanel ]-------

export function initDebugPanel() {
    const debugPanel = document.getElementById('debug-panel');
    const debugPanelClose = document.getElementById('debug-panel-close');
    const originalConsoleLog = console.log;
    const originalConsoleError = console.error;

    function debugLog(message, options = {}) {
        const isError = options.error || false;
        const show = options.show || false;

        const line = document.createElement('div');
        line.className = 'log-line ' + (isError ? 'log-error' : 'log-info');
        line.textContent = new Date().toLocaleTimeString() + ' | ' + message;
        debugPanel.appendChild(line);

        if (show) {
            debugPanel.classList.add('visible');
        }

        debugPanel.scrollTop = debugPanel.scrollHeight;

        const logLines = debugPanel.querySelectorAll('.log-line');
        if (logLines.length > 50) {
            logLines[0].remove();
        }
    }

    debugPanelClose.addEventListener('click', function() {
        debugPanel.classList.remove('visible');
    });

    function stringifyArg(a) {
        if (typeof a === 'string' || typeof a === 'number' || typeof a === 'boolean') {
            return String(a);
        }
        if (a instanceof Error) {
            return a.message + (a.stack ? '\n' + a.stack : '');
        }
        if (typeof a === 'object') {
            try {
                return JSON.stringify(a, null, 2);
            } catch (e) {
                return String(a);
            }
        }
        return String(a);
    }

    console.log = function(...args) {
        const lastArg = args[args.length - 1];
        const options = (typeof lastArg === 'object' && lastArg !== null && ('show' in lastArg || 'error' in lastArg)) ? args.pop() : {};
        const message = args.map(stringifyArg).join(' ');
        debugLog(message, options);
        originalConsoleLog.apply(console, args);
    };

    console.error = function(...args) {
        const lastArg = args[args.length - 1];
        const hasOptions = typeof lastArg === 'object' && lastArg !== null && ('show' in lastArg || 'error' in lastArg);
        const options = hasOptions ? args.pop() : {};
        const message = args.map(stringifyArg).join(' ');
        debugLog(message, { ...options, error: true, show: options.show !== false });
        originalConsoleError.apply(console, args);
    };
}

// #endregion

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
        setCardRemovedState(card, nextState);
        updateStoredArticleFromCard(card, article => ({
            ...article,
            removed: nextState
        }));
    });
}

// #endregion
