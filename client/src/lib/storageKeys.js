/**
 * Get the storage key for newsletter scrape data for a specific date.
 * @param {string} date - ISO date string (YYYY-MM-DD)
 * @returns {string} The storage key used for Supabase API endpoints
 */
export function getNewsletterScrapeKey(date) {
  return `newsletters:scrapes:${date}`
}
