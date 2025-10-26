/**
 * Cache Toggle UI Component
 * Manages the cache toggle UI and synchronizes with CacheSettings
 */

import { CacheSettings } from './cache-settings.js';

/**
 * Initialize cache toggle UI
 * Sets up event handlers and syncs UI with stored setting
 */
export function initCacheToggle() {
    const toggleInput = document.getElementById('cacheToggle');
    const statusText = document.querySelector('[data-testid="cache-toggle-status"]');

    if (!toggleInput || !statusText) {
        console.error('Cache toggle elements not found');
        return;
    }

    // Initialize toggle state from storage
    const isEnabled = CacheSettings.isCacheEnabled();
    toggleInput.checked = isEnabled;
    updateStatusText(statusText, isEnabled);

    // Handle toggle change
    toggleInput.addEventListener('change', (event) => {
        const newState = event.target.checked;
        CacheSettings.setCacheEnabled(newState);
        updateStatusText(statusText, newState);

        // Log the change for debugging
        console.log(`Cache ${newState ? 'enabled' : 'disabled'}`);
    });
}

/**
 * Update the status text based on cache state
 * @param {HTMLElement} statusElement - The status text element
 * @param {boolean} isEnabled - Whether cache is enabled
 */
function updateStatusText(statusElement, isEnabled) {
    statusElement.textContent = isEnabled ? '(enabled)' : '(disabled)';
}
