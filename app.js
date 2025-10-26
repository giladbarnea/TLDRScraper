/**
 * AppBootstrap wires feature bindings so the UI state machine starts in sync with backend data.
 */

import { bindCopySummaryFlow, bindRemovalControls, clipboardIconMarkup } from './ui-utils.js';
import { setDefaultDates, bindScrapeForm } from './scrape.js';
import { SUMMARY_EFFORT_OPTIONS, setupSummaryEffortControls, bindSummaryExpansion } from './summary.js';
import { bindTldrExpansion } from './tldr.js';
import { bindIssueToggleControls } from './issue.js';
import { hydrateRangeFromStore, renderPayloads } from './dom-builder.js';
import { initCacheToggle } from './cache-toggle.js';

// #region -------[ AppBootstrap ]-------

initCacheToggle();

setDefaultDates();

(function hydrateInitialRange() {
    const startInput = document.getElementById('start_date');
    const endInput = document.getElementById('end_date');
    if (!startInput || !endInput) return;
    const startValue = startInput.value;
    const endValue = endInput.value;
    if (!startValue || !endValue) return;
    const cachedPayloads = hydrateRangeFromStore(startValue, endValue);
    if (!cachedPayloads.length) return;
    renderPayloads(cachedPayloads, { source: 'local cache' }, setupSummaryEffortControls, SUMMARY_EFFORT_OPTIONS, clipboardIconMarkup);
    const result = document.getElementById('result');
    if (result) {
        result.className = 'success';
        result.style.display = 'block';
    }
})();

bindScrapeForm(setupSummaryEffortControls, SUMMARY_EFFORT_OPTIONS, clipboardIconMarkup);
bindCopySummaryFlow();
bindRemovalControls();
bindSummaryExpansion();
bindTldrExpansion();
bindIssueToggleControls();

// #endregion
