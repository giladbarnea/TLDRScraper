/**
 * useScraper - Handles newsletter scraping API calls
 * Manages scraping state, date range validation, and cache integration
 */
import { ref, computed } from 'vue'
import { useLocalStorage } from './useLocalStorage'
import { useCacheSettings } from './useCacheSettings'

export function useScraper() {
  const loading = ref(false)
  const error = ref(null)
  const progress = ref(0)
  const results = ref(null)

  const { enabled: cacheEnabled } = useCacheSettings()

  /**
   * Compute date range between start and end dates
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

  /**
   * Check if range is fully cached
   */
  function isRangeCached(startDate, endDate) {
    if (!cacheEnabled.value) return false

    const dates = computeDateRange(startDate, endDate)
    return dates.every(date => {
      const key = `newsletters:scrapes:${date}`
      return localStorage.getItem(key) !== null
    })
  }

  /**
   * Load cached data for date range
   */
  function loadFromCache(startDate, endDate) {
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

  /**
   * Build stats from payloads
   */
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

  /**
   * Merge payloads with cache
   */
  function mergeWithCache(payloads) {
    return payloads.map(payload => {
      const key = `newsletters:scrapes:${payload.date}`
      const { data } = useLocalStorage(key, null)

      if (data.value) {
        // Merge with existing
        const merged = {
          ...payload,
          articles: payload.articles.map(article => {
            const existing = data.value.articles?.find(a => a.url === article.url)
            if (existing) {
              return {
                ...article,
                summary: existing.summary || article.summary,
                tldr: existing.tldr || article.tldr,
                read: existing.read || article.read,
                removed: existing.removed ?? article.removed,
                tldrHidden: existing.tldrHidden ?? article.tldrHidden
              }
            }
            return article
          })
        }
        data.value = merged
        return merged
      } else {
        // Save new
        data.value = payload
        return payload
      }
    })
  }

  /**
   * Scrape newsletters from API
   */
  async function scrape(startDate, endDate) {
    error.value = null
    loading.value = true
    progress.value = 0
    results.value = null

    try {
      // Check if fully cached
      if (isRangeCached(startDate, endDate)) {
        const cached = loadFromCache(startDate, endDate)
        if (cached) {
          progress.value = 100
          results.value = cached
          return cached
        }
      }

      // Call API
      progress.value = 50
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
        // Build payloads from response
        const payloads = buildDailyPayloadsFromScrape(data)

        // Merge with cache if enabled
        const mergedPayloads = cacheEnabled.value
          ? mergeWithCache(payloads)
          : payloads

        progress.value = 100
        results.value = {
          success: true,
          payloads: mergedPayloads,
          source: 'Live scrape',
          stats: data.stats,
          debugLogs: data.stats?.debug_logs || []
        }

        return results.value
      } else {
        throw new Error(data.error || 'Scraping failed')
      }
    } catch (err) {
      error.value = err.message || 'Network error'
      console.error('Scraping error:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Build daily payloads from API response
   */
  function buildDailyPayloadsFromScrape(data) {
    const payloadByDate = new Map()
    const issuesByDate = new Map()

    // Process issues
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

    // Process articles
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

    // Build final payloads
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

    // Sort by date descending
    return payloads.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))
  }

  /**
   * Normalize ISO date string
   */
  function normalizeIsoDate(value) {
    if (typeof value !== 'string') return null
    const trimmed = value.trim()
    if (!trimmed) return null
    const date = new Date(trimmed)
    if (isNaN(date.getTime())) return null
    return date.toISOString().split('T')[0]
  }

  return {
    loading,
    error,
    progress,
    results,
    scrape,
    isRangeCached,
    loadFromCache
  }
}
