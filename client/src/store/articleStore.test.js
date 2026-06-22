import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// Each test gets a freshly-loaded store module (clears in-memory maps).
let store

beforeEach(async () => {
  vi.resetModules()
  if (typeof localStorage?.clear === 'function') localStorage.clear()
  if (typeof sessionStorage?.clear === 'function') sessionStorage.clear()
  store = await import('./articleStore.js')
})

function makeArticle(url, overrides = {}) {
  return {
    url,
    title: `Title for ${url}`,
    articleMeta: '5 min read',
    category: 'Test',
    sourceId: 'test-source',
    ...overrides,
  }
}

function makePayload(date, articles, overrides = {}) {
  return {
    date,
    articles,
    issues: [{ source_id: 'test-source', category: 'Test', subtitle: '' }],
    digest: null,
    storage_updated_at: null,
    ...overrides,
  }
}

describe('Test 1: same URL on different dates remains independent', () => {
  it('marking removed on date A does not flip the same URL on date B', () => {
    const url = 'example.com/x'
    store.ingestFeedPayloads([
      makePayload('2026-05-04', [makeArticle(url)]),
      makePayload('2026-05-05', [makeArticle(url)]),
    ])

    const keyA = `2026-05-04::${url}`
    const keyB = `2026-05-05::${url}`

    expect(keyA).not.toBe(keyB)
    expect(store.getSnapshotArticle(keyA)?.removed).toBe(false)
    expect(store.getSnapshotArticle(keyB)?.removed).toBe(false)

    store.applyArticlePatch(keyA, { removed: true })

    expect(store.getSnapshotArticle(keyA)?.removed).toBe(true)
    expect(store.getSnapshotArticle(keyB)?.removed).toBe(false)
    expect(store.getSnapshotDay('2026-05-04').articleKeys).toEqual([keyA])
    expect(store.getSnapshotDay('2026-05-05').articleKeys).toEqual([keyB])
  })
})

describe('Test 2: fresh scrape adds article to a cached date', () => {
  it('a second ingestion adding article B preserves A and surfaces B', () => {
    const date = '2026-05-04'
    const articleA = makeArticle('example.com/a')
    const articleB = makeArticle('example.com/b')
    const keyA = `${date}::${articleA.url}`
    const keyB = `${date}::${articleB.url}`

    store.ingestFeedPayloads([makePayload(date, [articleA])])
    expect(store.getSnapshotDay(date).articleKeys).toEqual([keyA])
    expect(store.getSnapshotArticle(keyB)).toBeNull()

    store.ingestFeedPayloads([makePayload(date, [articleA, articleB])])

    expect(store.getSnapshotDay(date).articleKeys).toEqual([keyA, keyB])
    expect(store.getSnapshotArticle(keyA)).not.toBeNull()
    expect(store.getSnapshotArticle(keyB)).not.toBeNull()
    expect(store.getSnapshotArticle(keyB).title).toBe(articleB.title)
  })

  it('preserves client-owned mutable fields on existing articles when fresh scrape arrives', () => {
    const date = '2026-05-04'
    const articleA = makeArticle('example.com/a')
    const articleB = makeArticle('example.com/b')
    const keyA = `${date}::${articleA.url}`

    store.ingestFeedPayloads([makePayload(date, [articleA])])
    store.applyArticlePatch(keyA, { read: { isRead: true, markedAt: '2026-05-04T12:00:00Z' } })
    expect(store.getSnapshotArticle(keyA).read.isRead).toBe(true)

    store.ingestFeedPayloads([makePayload(date, [articleA, articleB])])

    expect(store.getSnapshotArticle(keyA).read.isRead).toBe(true)
    expect(store.getSnapshotArticle(keyA).read.markedAt).toBe('2026-05-04T12:00:00Z')
  })
})

describe('expandFirstLeafAfterContainer: removal-driven auto-expansion', () => {
  const sectionArticle = (url, sourceId, sectionKey, sectionOrder) =>
    makeArticle(url, { sourceId, category: sourceId, section: sectionKey, sectionOrder })

  function expandedIds() {
    const raw = localStorage.getItem('expandedContainers:v1')
    return raw ? JSON.parse(raw) : []
  }

  it('expands the next sibling sections ancestors within the same source', () => {
    const date = '2026-05-04'
    const alpha = sectionArticle('s1/1', 'src1', 'Alpha', 0)
    const beta = sectionArticle('s1/2', 'src1', 'Beta', 1)
    store.ingestFeedPayloads([makePayload(date, [alpha, beta])])

    store.applyArticlePatch(`${date}::${alpha.url}`, { removed: true })  // Alpha exhausted
    store.interactionActions.expandFirstLeafAfterContainer(`section-${date}-src1-Alpha`)

    expect(expandedIds()).toEqual(expect.arrayContaining([
      `calendar-${date}`, `newsletter-${date}-src1`, `section-${date}-src1-Beta`,
    ]))
    expect(expandedIds()).not.toContain(`section-${date}-src1-Alpha`)
  })

  it('skips fully-removed sibling sections to reach the first available leaf', () => {
    const date = '2026-05-04'
    const alpha = sectionArticle('s1/1', 'src1', 'Alpha', 0)
    const beta = sectionArticle('s1/2', 'src1', 'Beta', 1)
    const gamma = sectionArticle('s1/3', 'src1', 'Gamma', 2)
    store.ingestFeedPayloads([makePayload(date, [alpha, beta, gamma])])

    store.applyArticlePatch(`${date}::${alpha.url}`, { removed: true })
    store.applyArticlePatch(`${date}::${beta.url}`, { removed: true })
    store.interactionActions.expandFirstLeafAfterContainer(`section-${date}-src1-Alpha`)

    expect(expandedIds()).toContain(`section-${date}-src1-Gamma`)
    expect(expandedIds()).not.toContain(`section-${date}-src1-Beta`)
  })

  it('falls back to the next source within the same day', () => {
    const date = '2026-05-04'
    const a = sectionArticle('s1/1', 'src1', 'Alpha', 0)
    const b = sectionArticle('s2/1', 'src2', 'Alpha', 0)
    store.ingestFeedPayloads([makePayload(date, [a, b])])

    store.applyArticlePatch(`${date}::${a.url}`, { removed: true })  // whole src1 exhausted
    store.interactionActions.expandFirstLeafAfterContainer(`newsletter-${date}-src1`)

    expect(expandedIds()).toEqual(expect.arrayContaining([
      `calendar-${date}`, `newsletter-${date}-src2`, `section-${date}-src2-Alpha`,
    ]))
  })

  it('falls back to the next days first leaf', () => {
    const a = sectionArticle('s1/1', 'src1', 'Alpha', 0)
    const b = sectionArticle('s1/1', 'src1', 'Alpha', 0)
    store.ingestFeedPayloads([
      makePayload('2026-05-04', [a]),
      makePayload('2026-05-05', [b]),
    ])

    store.applyArticlePatch(`2026-05-04::${a.url}`, { removed: true })  // whole day exhausted
    store.interactionActions.expandFirstLeafAfterContainer('calendar-2026-05-04')

    expect(expandedIds()).toEqual(expect.arrayContaining([
      'calendar-2026-05-05', 'newsletter-2026-05-05-src1', 'section-2026-05-05-src1-Alpha',
    ]))
  })

  it('does nothing when there is no later available leaf', () => {
    const date = '2026-05-04'
    const a = sectionArticle('s1/1', 'src1', 'Alpha', 0)
    store.ingestFeedPayloads([makePayload(date, [a])])

    store.applyArticlePatch(`${date}::${a.url}`, { removed: true })
    store.interactionActions.expandFirstLeafAfterContainer(`section-${date}-src1-Alpha`)

    expect(localStorage.getItem('expandedContainers:v1')).toBeNull()
  })

  // Manually collapsing a container twice via short press leaves it folded AND
  // flagged as user-collapsed (the second press collapses an expanded container).
  function manuallyCollapse(containerId) {
    store.interactionActions.containerShortPress(containerId)  // fold -> expand
    store.interactionActions.containerShortPress(containerId)  // expand -> fold (explicit)
  }

  it('does not re-open a container the user explicitly collapsed; skips to the next available leaf', () => {
    const date = '2026-05-04'
    const alpha = sectionArticle('s1/1', 'src1', 'Alpha', 0)
    const beta = sectionArticle('s1/2', 'src1', 'Beta', 1)
    const gamma = sectionArticle('s2/1', 'src2', 'Gamma', 0)
    store.ingestFeedPayloads([makePayload(date, [alpha, beta, gamma])])

    manuallyCollapse(`section-${date}-src1-Beta`)            // user closes Beta deliberately
    store.applyArticlePatch(`${date}::${alpha.url}`, { removed: true })  // Alpha exhausted
    store.interactionActions.expandFirstLeafAfterContainer(`section-${date}-src1-Alpha`)

    const expanded = JSON.parse(localStorage.getItem('expandedContainers:v1') ?? '[]')
    expect(expanded, `user-collapsed Beta must stay folded, got ${JSON.stringify(expanded)}`)
      .not.toContain(`section-${date}-src1-Beta`)
    expect(expanded, `should skip past Beta to Gamma, got ${JSON.stringify(expanded)}`)
      .toContain(`section-${date}-src2-Gamma`)
  })

  it('exposes nothing when the only later leaf is inside a user-collapsed container', () => {
    const date = '2026-05-04'
    const alpha = sectionArticle('s1/1', 'src1', 'Alpha', 0)
    const beta = sectionArticle('s1/2', 'src1', 'Beta', 1)
    store.ingestFeedPayloads([makePayload(date, [alpha, beta])])

    manuallyCollapse(`section-${date}-src1-Beta`)
    store.applyArticlePatch(`${date}::${alpha.url}`, { removed: true })
    store.interactionActions.expandFirstLeafAfterContainer(`section-${date}-src1-Alpha`)

    const expanded = JSON.parse(localStorage.getItem('expandedContainers:v1') ?? '[]')
    expect(expanded, `no container should be auto-expanded, got ${JSON.stringify(expanded)}`)
      .not.toContain(`section-${date}-src1-Beta`)
  })
})

describe('Test 3: stale article on refresh prunes selection', () => {
  it('refresh that drops a selected article removes it and clears select-mode if it was the only selection', () => {
    const date = '2026-05-04'
    const articleA = makeArticle('example.com/a')
    const articleB = makeArticle('example.com/b')
    const keyB = `${date}::${articleB.url}`

    store.ingestFeedPayloads([makePayload(date, [articleA, articleB])])
    store.applyArticlePatch(keyB, { selected: true })

    const selected = renderHook(() => store.useSelectedArticles())
    const isSelectMode = renderHook(() => store.useIsSelectMode())

    expect(selected.result.current.map(d => d.key)).toEqual([keyB])
    expect(isSelectMode.result.current).toBe(true)

    store.ingestFeedPayloads([makePayload(date, [articleA])])

    expect(store.getSnapshotArticle(keyB)).toBeNull()
    expect(store.getSnapshotDay(date).articleKeys).not.toContain(keyB)

    selected.rerender()
    isSelectMode.rerender()
    expect(selected.result.current).toEqual([])
    expect(isSelectMode.result.current).toBe(false)
  })
})
