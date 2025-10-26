/**
 * Cache Settings Module
 * Manages the cache toggle setting for localStorage operations
 */

const CACHE_SETTING_KEY = 'cache:enabled';

export const CacheSettings = (() => {
    /**
     * Check if cache is enabled
     * @returns {boolean} true if cache is enabled, false otherwise
     */
    function isCacheEnabled() {
        const stored = localStorage.getItem(CACHE_SETTING_KEY);
        // Default to true (cache enabled) if not set
        if (stored === null) {
            return true;
        }
        return stored === 'true';
    }

    /**
     * Set cache enabled state
     * @param {boolean} enabled - true to enable cache, false to disable
     */
    function setCacheEnabled(enabled) {
        localStorage.setItem(CACHE_SETTING_KEY, String(enabled));
    }

    /**
     * Toggle cache enabled state
     * @returns {boolean} new state after toggle
     */
    function toggleCache() {
        const current = isCacheEnabled();
        const newState = !current;
        setCacheEnabled(newState);
        return newState;
    }

    return {
        isCacheEnabled,
        setCacheEnabled,
        toggleCache
    };
})();
