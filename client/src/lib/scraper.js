/**
 * Plain JS scraper utilities for React components
 * Extracted from composables/useScraper.js
 */

function computeDateRange(startDate, endDate) {
  const dates = []
  const start = new Date(startDate)
  const end = new Date(endDate)

  if (isNaN(start.getTime()) || isNaN(end.getTime())) {
    return []
  }

  if (start > end) return []

  const current = new Date(end)
  while (current >= start) {
    dates.push(current.toISOString().split('T')[0])
    current.setDate(current.getDate() - 1)
  }

  return dates
}

function buildStatsFromPayloads(payloads) {
  const uniqueUrls = new Set()
  let totalArticles = 0

  payloads.forEach(payload => {
    if (payload.articles) {
      payload.articles.forEach(article => {
        uniqueUrls.add(article.url)
        totalArticles++
      })
    }
  })

  return {
    total_articles: totalArticles,
    unique_urls: uniqueUrls.size,
    dates_processed: payloads.length,
    dates_with_content: payloads.filter(p => p.articles?.length > 0).length
  }
}

function isRangeCached(startDate, endDate, cacheEnabled) {
  if (!cacheEnabled) return false

  const dates = computeDateRange(startDate, endDate)
  return dates.every(date => {
    const key = `newsletters:scrapes:${date}`
    return localStorage.getItem(key) !== null
  })
}

function normalizeIsoDate(value) {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  if (!trimmed) return null
  const date = new Date(trimmed)
  if (isNaN(date.getTime())) return null
  return date.toISOString().split('T')[0]
}

function buildDailyPayloadsFromScrape(data) {
  const payloadByDate = new Map()
  const issuesByDate = new Map()

  if (Array.isArray(data.issues)) {
    data.issues.forEach(issue => {
      const date = normalizeIsoDate(issue.date)
      if (!date) return

      if (!issuesByDate.has(date)) {
        issuesByDate.set(date, [])
      }
      issuesByDate.get(date).push(issue)
    })
  }

  if (Array.isArray(data.articles)) {
    data.articles.forEach(article => {
      const date = normalizeIsoDate(article.date)
      if (!date) return

      const articleData = {
        url: article.url,
        title: article.title || article.url,
        issueDate: date,
        category: article.category || 'Newsletter',
        sourceId: article.source_id || null,
        section: article.section_title || null,
        sectionEmoji: article.section_emoji || null,
        sectionOrder: article.section_order ?? null,
        newsletterType: article.newsletter_type || null,
        removed: Boolean(article.removed),
        tldrHidden: false,
        summary: { status: 'unknown', markdown: '', effort: 'low', checkedAt: null, errorMessage: null },
        tldr: { status: 'unknown', markdown: '', effort: 'low', checkedAt: null, errorMessage: null },
        read: { isRead: false, markedAt: null }
      }

      if (!payloadByDate.has(date)) {
        payloadByDate.set(date, [])
      }
      payloadByDate.get(date).push(articleData)
    })
  }

  const payloads = []
  payloadByDate.forEach((articles, date) => {
    const issues = issuesByDate.get(date) || []
    payloads.push({
      date,
      cachedAt: new Date().toISOString(),
      articles,
      issues
    })
  })

  return payloads.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))
}

function mergeWithCache(payloads) {
  return payloads.map(payload => {
    const key = `newsletters:scrapes:${payload.date}`
    const raw = localStorage.getItem(key)

    if (raw) {
      try {
        const existing = JSON.parse(raw)
        const merged = {
          ...payload,
          articles: payload.articles.map(article => {
            const existingArticle = existing.articles?.find(a => a.url === article.url)
            if (existingArticle) {
              return {
                ...article,
                summary: existingArticle.summary || article.summary,
                tldr: existingArticle.tldr || article.tldr,
                read: existingArticle.read || article.read,
                removed: existingArticle.removed ?? article.removed,
                tldrHidden: existingArticle.tldrHidden ?? article.tldrHidden
              }
            }
            return article
          })
        }
        localStorage.setItem(key, JSON.stringify(merged))
        return merged
      } catch (err) {
        console.error(`Failed to merge with cache for ${payload.date}:`, err)
        localStorage.setItem(key, JSON.stringify(payload))
        return payload
      }
    } else {
      localStorage.setItem(key, JSON.stringify(payload))
      return payload
    }
  })
}

export function loadFromCache(startDate, endDate) {
  const dates = computeDateRange(startDate, endDate)
  const payloads = []

  dates.forEach(date => {
    const key = `newsletters:scrapes:${date}`
    const raw = localStorage.getItem(key)
    if (raw) {
      try {
        const payload = JSON.parse(raw)
        payloads.push(payload)
      } catch (err) {
        console.error(`Failed to parse cached data for ${date}:`, err)
      }
    }
  })

  return payloads.length > 0 ? {
    success: true,
    payloads,
    source: 'local cache',
    stats: buildStatsFromPayloads(payloads)
  } : null
}

function collectExcludedUrls() {
  const excluded = new Set()

  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key && key.startsWith('newsletters:scrapes:')) {
      const raw = localStorage.getItem(key)
      if (raw) {
        try {
          const payload = JSON.parse(raw)
          if (payload.articles) {
            for (const article of payload.articles) {
              if (article.removed || article.read?.isRead) {
                excluded.add(article.url)
              }
            }
          }
        } catch (err) {
          console.error(`Failed to parse cached data for ${key}:`, err)
        }
      }
    }
  }

  return Array.from(excluded)
}

export async function scrapeNewsletters(startDate, endDate, cacheEnabled = true) {
  if (isRangeCached(startDate, endDate, cacheEnabled)) {
    const cached = loadFromCache(startDate, endDate)
    if (cached) {
      return cached
    }
  }

  const excludedUrls = collectExcludedUrls()

  const response = await window.fetch('/api/scrape', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_date: startDate,
      end_date: endDate,
      excluded_urls: excludedUrls
    })
  })

  const data = await response.json()

  if (data.success) {
    const payloads = buildDailyPayloadsFromScrape(data)
    const mergedPayloads = cacheEnabled ? mergeWithCache(payloads) : payloads

    return {
      success: true,
      payloads: mergedPayloads,
      source: 'Live scrape',
      stats: data.stats,
      debugLogs: data.stats?.debug_logs || []
    }
  } else {
    throw new Error(data.error || 'Scraping failed')
  }
}
