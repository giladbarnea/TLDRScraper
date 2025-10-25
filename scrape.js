/**
 * ScrapeIntake validates date ranges, calls /api/scrape, and reconstructs the article card surface for downstream features.
 */

import { ClientStorage } from './storage.js';
import {
    computeDateRange,
    buildDailyPayloadsFromScrape,
    hydrateRangeFromStore,
    renderPayloads
} from './dom-builder.js';

// #region -------[ ScrapeIntake ]-------

export function setDefaultDates() {
    const today = new Date();
    const threeDaysAgo = new Date(today);
    threeDaysAgo.setDate(today.getDate() - 3);

    const endInput = document.getElementById('end_date');
    const startInput = document.getElementById('start_date');
    if (endInput) {
        endInput.value = today.toISOString().split('T')[0];
    }
    if (startInput) {
        startInput.value = threeDaysAgo.toISOString().split('T')[0];
    }
}

export function bindScrapeForm(setupSummaryEffortControls, SUMMARY_EFFORT_OPTIONS, clipboardIconMarkup) {
    const form = document.getElementById('scrapeForm');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const startDate = document.getElementById('start_date').value;
        const endDate = document.getElementById('end_date').value;

        const button = document.getElementById('scrapeBtn');
        const progress = document.getElementById('progress');
        const result = document.getElementById('result');

        const start = new Date(startDate);
        const end = new Date(endDate);

        if (start > end) {
            result.style.display = 'block';
            result.className = 'error';
            result.textContent = 'Start date must be before or equal to end date.';
            return;
        }

        const daysDiff = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
        if (daysDiff >= 31) {
            result.style.display = 'block';
            result.className = 'error';
            result.textContent = 'Date range cannot exceed 31 days. Please select a smaller range.';
            return;
        }

        const rangeDates = computeDateRange(startDate, endDate);
        const cachedPayloads = hydrateRangeFromStore(startDate, endDate);
        if (rangeDates.length > 0 && cachedPayloads.length === rangeDates.length) {
            renderPayloads(cachedPayloads, { source: 'local cache' }, setupSummaryEffortControls, SUMMARY_EFFORT_OPTIONS, clipboardIconMarkup);
            result.className = 'success';
            result.style.display = 'block';
            document.getElementById('progress-fill').style.width = '100%';
            progress.style.display = 'none';
            button.disabled = false;
            return;
        }

        button.disabled = true;
        progress.style.display = 'block';
        result.style.display = 'none';

        document.getElementById('progress-text').textContent = 'Scraping newsletters... This may take several minutes.';
        document.getElementById('progress-fill').style.width = '50%';

        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start_date: startDate, end_date: endDate })
            });

            const data = await response.json();

            if (data.success) {
                const payloads = buildDailyPayloadsFromScrape(data);
                payloads.forEach(payload => {
                    ClientStorage.mergeDay(payload.date, payload);
                });

                const hydratedPayloads = hydrateRangeFromStore(startDate, endDate);
                renderPayloads(hydratedPayloads, { stats: data.stats, source: 'Live scrape' }, setupSummaryEffortControls, SUMMARY_EFFORT_OPTIONS, clipboardIconMarkup);

                try {
                    if (Array.isArray(data.stats.debug_logs) && data.stats.debug_logs.length) {
                        const slot = document.getElementById('logs-slot');
                        if (slot) {
                            const details = document.createElement('details');
                            const summary = document.createElement('summary');
                            summary.textContent = 'Debug logs';
                            const pre = document.createElement('pre');
                            pre.style.whiteSpace = 'pre-wrap';
                            pre.textContent = data.stats.debug_logs.map(l => String(l)).join('\n');
                            details.appendChild(summary);
                            details.appendChild(pre);
                            slot.appendChild(details);
                        }
                    }
                } catch (_) {}

                result.className = 'success';
                document.getElementById('progress-fill').style.width = '100%';

                setTimeout(() => {
                    const firstH1 = document.querySelector('main#write h1');
                    if (firstH1) {
                        firstH1.scrollIntoView({ behavior: 'smooth' });
                    }
                }, 100);
            } else {
                result.style.display = 'block';
                result.className = 'error';
                result.textContent = 'Error: ' + data.error;
            }

        } catch (error) {
            result.style.display = 'block';
            result.className = 'error';
            result.textContent = 'Network error: ' + error.message;
            console.error('Scraping error:', error);
        }

        progress.style.display = 'none';
        button.disabled = false;
    });
}

// #endregion
