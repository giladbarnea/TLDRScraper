import * as storageApi from './storageApi'

/**
 * Plain JS scraper utilities for React components
 * Extracted from composables/useScraper.js
 */

export async function scrapeNewsletters(startDate, endDate, cacheEnabled = true, signal) {
  const response = await window.fetch('/api/scrape', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_date: startDate,
      end_date: endDate
    }),
    signal
  })

  const data = await response.json()

  if (data.success) {
    return {
      success: true,
      payloads: data.payloads || [],
      source: data.source || 'Live scrape',
      stats: data.stats
    }
  } else {
    throw new Error(data.error || 'Scraping failed')
  }
}

export async function fetchCachedPayloadsRange(startDate, endDate, signal) {
  const payloads = await storageApi.getDailyPayloadsRange(startDate, endDate, signal)

  return {
    success: true,
    payloads,
    source: 'Supabase cache',
    stats: null
  }
}
