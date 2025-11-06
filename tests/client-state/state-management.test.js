/**
 * Node.js unit tests for TLDRScraper client state management
 *
 * Tests the pure JavaScript logic extracted from React components.
 * No browser required - uses localStorage polyfill.
 *
 * Run with: node tests/client-state/state-management.test.js
 */

// ============================================================================
// SETUP: localStorage Polyfill
// ============================================================================

class LocalStorage {
  constructor() {
    this.store = new Map()
  }

  getItem(key) {
    return this.store.get(key) ?? null
  }

  setItem(key, value) {
    this.store.set(key, String(value))
  }

  removeItem(key) {
    this.store.delete(key)
  }

  clear() {
    this.store.clear()
  }

  key(index) {
    return Array.from(this.store.keys())[index] ?? null
  }

  get length() {
    return this.store.size
  }
}

global.localStorage = new LocalStorage()

// ============================================================================
// INLINE: Core logic from client/src/lib/storageKeys.js
// ============================================================================

function getNewsletterScrapeKey(date) {
  return `newsletters:scrapes:${date}`
}

// ============================================================================
// INLINE: Core logic from client/src/lib/scraper.js
// ============================================================================

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
    const key = getNewsletterScrapeKey(payload.date)
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

// ============================================================================
// TEST UTILITIES
// ============================================================================

let testsPassed = 0
let testsFailed = 0

function assert(condition, message) {
  if (!condition) {
    console.error(`  ✗ FAILED: ${message}`)
    testsFailed++
    throw new Error(`Assertion failed: ${message}`)
  }
  console.log(`  ✓ ${message}`)
  testsPassed++
}

function test(name, fn) {
  console.log(`\n${name}`)
  try {
    fn()
    console.log(`  PASSED`)
  } catch (err) {
    console.error(`  FAILED: ${err.message}`)
  }
}

// ============================================================================
// TESTS
// ============================================================================

console.log('='.repeat(70))
console.log('CLIENT STATE MANAGEMENT TESTS')
console.log('='.repeat(70))

// Test 1: Basic merge - no cache exists
test('Test 1: Initial scrape stores articles in localStorage', () => {
  localStorage.clear()

  const scrapeData = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01' },
      { url: 'https://example.com/2', title: 'Article 2', date: '2024-11-01' }
    ]
  }

  const payloads = buildDailyPayloadsFromScrape(scrapeData)
  const merged = mergeWithCache(payloads)

  assert(merged.length === 1, 'Should have 1 payload')
  assert(merged[0].articles.length === 2, 'Should have 2 articles')
  assert(merged[0].articles[0].removed === false, 'Article should not be removed initially')

  const cached = localStorage.getItem('newsletters:scrapes:2024-11-01')
  assert(cached !== null, 'Should store in localStorage')

  const parsed = JSON.parse(cached)
  assert(parsed.articles.length === 2, 'Cached data should have 2 articles')
})

// Test 2: Remove article and verify persistence
test('Test 2: Marking article as removed persists in localStorage', () => {
  localStorage.clear()

  // Initial scrape
  const scrapeData = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01' },
      { url: 'https://example.com/2', title: 'Article 2', date: '2024-11-01' }
    ]
  }

  const payloads = buildDailyPayloadsFromScrape(scrapeData)
  mergeWithCache(payloads)

  // Simulate user clicking "Remove" on first article
  const key = 'newsletters:scrapes:2024-11-01'
  const cached = JSON.parse(localStorage.getItem(key))
  cached.articles[0].removed = true
  localStorage.setItem(key, JSON.stringify(cached))

  // Verify it was marked
  const updated = JSON.parse(localStorage.getItem(key))
  assert(updated.articles[0].removed === true, 'Article should be marked as removed')
  assert(updated.articles[1].removed === false, 'Other article should not be affected')
})

// Test 3: THE CRITICAL TEST - Re-scrape preserves removed state
test('Test 3: Re-scraping same date preserves removed article state', () => {
  localStorage.clear()

  // Initial scrape
  const scrapeData = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01' },
      { url: 'https://example.com/2', title: 'Article 2', date: '2024-11-01' }
    ]
  }

  const payloads1 = buildDailyPayloadsFromScrape(scrapeData)
  mergeWithCache(payloads1)

  // User marks first article as removed
  const key = 'newsletters:scrapes:2024-11-01'
  const cached = JSON.parse(localStorage.getItem(key))
  cached.articles[0].removed = true
  localStorage.setItem(key, JSON.stringify(cached))

  // User re-scrapes (server returns fresh data with removed=false)
  const scrapeData2 = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01', removed: false },
      { url: 'https://example.com/2', title: 'Article 2', date: '2024-11-01', removed: false }
    ]
  }

  const payloads2 = buildDailyPayloadsFromScrape(scrapeData2)
  const merged = mergeWithCache(payloads2)

  // CRITICAL ASSERTION: Removed state should persist
  assert(merged[0].articles[0].removed === true, 'First article should still be removed after re-scrape')
  assert(merged[0].articles[1].removed === false, 'Second article should not be removed')

  // Verify localStorage was updated correctly
  const finalCached = JSON.parse(localStorage.getItem(key))
  assert(finalCached.articles[0].removed === true, 'Removed state should persist in cache')
})

// Test 4: TLDR state persists
test('Test 4: TLDR content persists across re-scrapes', () => {
  localStorage.clear()

  // Initial scrape
  const scrapeData = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01' }
    ]
  }

  const payloads1 = buildDailyPayloadsFromScrape(scrapeData)
  mergeWithCache(payloads1)

  // User fetches TLDR
  const key = 'newsletters:scrapes:2024-11-01'
  const cached = JSON.parse(localStorage.getItem(key))
  cached.articles[0].tldr = {
    status: 'success',
    markdown: '## This is a TLDR',
    effort: 'low',
    checkedAt: new Date().toISOString(),
    errorMessage: null
  }
  localStorage.setItem(key, JSON.stringify(cached))

  // Re-scrape
  const scrapeData2 = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01' }
    ]
  }

  const payloads2 = buildDailyPayloadsFromScrape(scrapeData2)
  const merged = mergeWithCache(payloads2)

  assert(merged[0].articles[0].tldr.status === 'success', 'TLDR status should persist')
  assert(merged[0].articles[0].tldr.markdown === '## This is a TLDR', 'TLDR content should persist')
})

// Test 5: Read state persists
test('Test 5: Read state persists across re-scrapes', () => {
  localStorage.clear()

  // Initial scrape
  const scrapeData = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01' }
    ]
  }

  const payloads1 = buildDailyPayloadsFromScrape(scrapeData)
  mergeWithCache(payloads1)

  // User marks as read
  const key = 'newsletters:scrapes:2024-11-01'
  const cached = JSON.parse(localStorage.getItem(key))
  const readAt = new Date().toISOString()
  cached.articles[0].read = { isRead: true, markedAt: readAt }
  localStorage.setItem(key, JSON.stringify(cached))

  // Re-scrape
  const scrapeData2 = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01' }
    ]
  }

  const payloads2 = buildDailyPayloadsFromScrape(scrapeData2)
  const merged = mergeWithCache(payloads2)

  assert(merged[0].articles[0].read.isRead === true, 'Read state should persist')
  assert(merged[0].articles[0].read.markedAt === readAt, 'Read timestamp should persist')
})

// Test 6: Multiple articles with mixed states
test('Test 6: Complex scenario - multiple articles with different states', () => {
  localStorage.clear()

  // Initial scrape with 3 articles
  const scrapeData = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01' },
      { url: 'https://example.com/2', title: 'Article 2', date: '2024-11-01' },
      { url: 'https://example.com/3', title: 'Article 3', date: '2024-11-01' }
    ]
  }

  const payloads1 = buildDailyPayloadsFromScrape(scrapeData)
  mergeWithCache(payloads1)

  // User interactions:
  // - Article 1: Removed
  // - Article 2: Read + TLDR fetched
  // - Article 3: No interaction
  const key = 'newsletters:scrapes:2024-11-01'
  const cached = JSON.parse(localStorage.getItem(key))

  cached.articles[0].removed = true

  cached.articles[1].read = { isRead: true, markedAt: new Date().toISOString() }
  cached.articles[1].tldr = {
    status: 'success',
    markdown: '## TLDR for Article 2',
    effort: 'low',
    checkedAt: new Date().toISOString(),
    errorMessage: null
  }

  localStorage.setItem(key, JSON.stringify(cached))

  // Re-scrape
  const scrapeData2 = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01' },
      { url: 'https://example.com/2', title: 'Article 2', date: '2024-11-01' },
      { url: 'https://example.com/3', title: 'Article 3', date: '2024-11-01' }
    ]
  }

  const payloads2 = buildDailyPayloadsFromScrape(scrapeData2)
  const merged = mergeWithCache(payloads2)

  // Assertions
  assert(merged[0].articles[0].removed === true, 'Article 1 should still be removed')
  assert(merged[0].articles[1].read.isRead === true, 'Article 2 should still be read')
  assert(merged[0].articles[1].tldr.status === 'success', 'Article 2 TLDR should persist')
  assert(merged[0].articles[2].removed === false, 'Article 3 should have no state changes')
  assert(merged[0].articles[2].read.isRead === false, 'Article 3 should not be read')
})

// Test 7: New article appears in re-scrape
test('Test 7: New articles appear correctly when re-scraping', () => {
  localStorage.clear()

  // Initial scrape with 2 articles
  const scrapeData = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01' },
      { url: 'https://example.com/2', title: 'Article 2', date: '2024-11-01' }
    ]
  }

  const payloads1 = buildDailyPayloadsFromScrape(scrapeData)
  mergeWithCache(payloads1)

  // Mark first as removed
  const key = 'newsletters:scrapes:2024-11-01'
  const cached = JSON.parse(localStorage.getItem(key))
  cached.articles[0].removed = true
  localStorage.setItem(key, JSON.stringify(cached))

  // Re-scrape with a NEW third article
  const scrapeData2 = {
    articles: [
      { url: 'https://example.com/1', title: 'Article 1', date: '2024-11-01' },
      { url: 'https://example.com/2', title: 'Article 2', date: '2024-11-01' },
      { url: 'https://example.com/3', title: 'Article 3 (NEW)', date: '2024-11-01' }
    ]
  }

  const payloads2 = buildDailyPayloadsFromScrape(scrapeData2)
  const merged = mergeWithCache(payloads2)

  assert(merged[0].articles.length === 3, 'Should have 3 articles after re-scrape')
  assert(merged[0].articles[0].removed === true, 'First article should still be removed')
  assert(merged[0].articles[1].removed === false, 'Second article should not be removed')
  assert(merged[0].articles[2].removed === false, 'New article should not be removed')
  assert(merged[0].articles[2].title === 'Article 3 (NEW)', 'New article should have correct data')
})

// ============================================================================
// SUMMARY
// ============================================================================

console.log('\n' + '='.repeat(70))
console.log('TEST SUMMARY')
console.log('='.repeat(70))
console.log(`✓ Passed: ${testsPassed}`)
console.log(`✗ Failed: ${testsFailed}`)
console.log(`Total: ${testsPassed + testsFailed}`)

if (testsFailed === 0) {
  console.log('\n🎉 ALL TESTS PASSED! State management logic is working correctly.')
  process.exit(0)
} else {
  console.log(`\n❌ ${testsFailed} test(s) failed. State management has bugs.`)
  process.exit(1)
}
