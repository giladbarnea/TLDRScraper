/**
 * Plain JS scraper utilities for React components
 * Extracted from composables/useScraper.js
 */

import * as storageApi from './storageApi'

function computeDateRange(startDate, endDate) {
  const dates = []
  const start = new Date(startDate)
  const end = new Date(endDate)

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
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

async function isRangeCached(startDate, endDate, cacheEnabled) {
  if (!cacheEnabled) return false

  const dates = computeDateRange(startDate, endDate)

  // Bypass cache if "today" is in range (server will handle union)
  const todayStr = new Date().toISOString().split('T')[0]
  if (dates.includes(todayStr)) {
    return false
  }

  for (const date of dates) {
    const isCached = await storageApi.isDateCached(date)
    if (!isCached) {
      return false
    }
  }

  return true
}

function normalizeIsoDate(value) {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  if (!trimmed) return null
  const date = new Date(trimmed)
  if (Number.isNaN(date.getTime())) return null
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
        articleMeta: article.article_meta || "",
        issueDate: date,
        category: article.category || 'Newsletter',
        sourceId: article.source_id || null,
        section: article.section_title || null,
        sectionEmoji: article.section_emoji || null,
        sectionOrder: article.section_order ?? null,
        newsletterType: article.newsletter_type || null,
        removed: Boolean(article.removed),
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
      articles,
      issues
    })
  })

  return payloads.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))
}

async function mergeWithCache(payloads) {
  const merged = []

  for (const payload of payloads) {
    const existing = await storageApi.getDailyPayload(payload.date)

    if (existing) {
      const mergedPayload = {
        ...payload,
        articles: payload.articles.map(article => {
          const existingArticle = existing.articles?.find(a => a.url === article.url)
          if (existingArticle) {
            return {
              ...article,
              tldr: existingArticle.tldr || article.tldr,
              read: existingArticle.read || article.read,
              removed: existingArticle.removed ?? article.removed
            }
          }
          return article
        })
      }

      await storageApi.setDailyPayload(payload.date, mergedPayload)
      merged.push(mergedPayload)
    } else {
      await storageApi.setDailyPayload(payload.date, payload)
      merged.push(payload)
    }
  }

  return merged
}

export async function loadFromCache(startDate, endDate, signal) {
  const payloads = await storageApi.getDailyPayloadsRange(startDate, endDate, signal)

  if (!payloads || payloads.length === 0) {
    return null
  }

  return {
    success: true,
    payloads,
    source: 'local cache',
    stats: buildStatsFromPayloads(payloads)
  }
}

export async function scrapeNewsletters(startDate, endDate, cacheEnabled = true) {
  if (await isRangeCached(startDate, endDate, cacheEnabled)) {
    const cached = await loadFromCache(startDate, endDate)
    if (cached) {
      return cached
    }
  }

  const response = await window.fetch('/api/scrape', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_date: startDate,
      end_date: endDate
    })
  })

  const data = await response.json()

  if (data.success) {
    const payloads = buildDailyPayloadsFromScrape(data)
    const mergedPayloads = cacheEnabled ? await mergeWithCache(payloads) : payloads

    return {
      success: true,
      payloads: mergedPayloads,
      source: 'Live scrape',
      stats: data.stats
    }
  } else {
    throw new Error(data.error || 'Scraping failed')
  }
}
