/**
 * Plain JS scraper utilities for React components
 * Extracted from composables/useScraper.js
 */

import { formatYaml } from './yamlLog'

function summarizeScrapeResponse(data) {
  const payloads = (data.payloads || []).map((payload) => ({
    date: payload.date,
    article_count: (payload.articles || []).length,
    article_urls: (payload.articles || []).map((article) => article.url),
  }))

  return {
    success: data.success,
    source: data.source,
    stats: data.stats,
    payload_count: payloads.length,
    total_articles: payloads.reduce((sum, p) => sum + p.article_count, 0),
    payloads,
  }
}

export async function scrapeNewsletters(startDate, endDate, signal) {
  const requestPayload = { start_date: startDate, end_date: endDate }
  console.log(`scrape_request:\n${formatYaml(requestPayload, 1)}`)

  const response = await window.fetch('/api/scrape', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestPayload),
    signal,
  })

  const data = await response.json()

  if (data.success) {
    console.log(`scrape_response:\n${formatYaml(summarizeScrapeResponse(data), 1)}`)
    return {
      success: true,
      payloads: data.payloads || [],
      source: data.source || 'Live scrape',
      stats: data.stats,
    }
  }

  const errorMessage = data.error || 'Scraping failed'
  console.error(`/api/scrape failed: ${errorMessage}`)
  console.log(`scrape_response:\n${formatYaml({ success: false, error: data.error }, 1)}`)
  throw new Error(errorMessage)
}
