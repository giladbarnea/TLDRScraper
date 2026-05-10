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
