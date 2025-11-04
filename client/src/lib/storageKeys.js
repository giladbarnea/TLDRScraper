export const STORAGE_KEYS = {
  CACHE_ENABLED: 'cache:enabled'
}

/**
 * Get the localStorage key for newsletter scrape data for a specific date.
 * @param {string} date - ISO date string (YYYY-MM-DD)
 * @returns {string} The localStorage key
 */
export function getNewsletterScrapeKey(date) {
  return `newsletters:scrapes:${date}`
}
