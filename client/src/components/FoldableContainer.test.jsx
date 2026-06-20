import { render } from '@testing-library/react'
import { StrictMode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// Fresh store + component per test so module-level state and localStorage don't leak.
let store
let FoldableContainer

beforeEach(async () => {
  vi.resetModules()
  if (typeof localStorage?.clear === 'function') localStorage.clear()
  store = await import('../store/articleStore.js')
  FoldableContainer = (await import('./FoldableContainer.jsx')).default
})

const DATE = '2026-05-04'
const ALPHA_ID = `section-${DATE}-src1-Alpha`
const BETA_ID = `section-${DATE}-src1-Beta`

function seedTwoSections() {
  store.ingestFeedPayloads([{
    date: DATE,
    articles: [
      { url: 's1/1', title: 'A', category: 'src1', sourceId: 'src1', section: 'Alpha', sectionOrder: 0 },
      { url: 's1/2', title: 'B', category: 'src1', sourceId: 'src1', section: 'Beta', sectionOrder: 1 },
    ],
    issues: [{ source_id: 'src1', category: 'src1', subtitle: '' }],
    digest: null,
    storage_updated_at: null,
  }])
}

function expandedIds() {
  const raw = localStorage.getItem('expandedContainers:v1')
  return raw ? JSON.parse(raw) : []
}

function renderFolded(id, defaultFolded) {
  return render(
    <StrictMode>
      <FoldableContainer id={id} title="t" defaultFolded={defaultFolded}>x</FoldableContainer>
    </StrictMode>
  )
}

describe('FoldableContainer auto-expand on exhaustion', () => {
  // The user clears a section while reading: the container transitions to folded
  // mid-session, and the next available section's first card should be exposed.
  it('exposes the next sections card when a section is exhausted during the session', () => {
    seedTwoSections()
    const { rerender } = renderFolded(ALPHA_ID, false)  // Alpha starts populated

    store.applyArticlePatch(`${DATE}::s1/1`, { removed: true })  // exhaust Alpha
    rerender(
      <StrictMode>
        <FoldableContainer id={ALPHA_ID} title="t" defaultFolded={true}>x</FoldableContainer>
      </StrictMode>
    )

    expect(expandedIds(), `next section Beta should be exposed, got ${JSON.stringify(expandedIds())}`)
      .toContain(BETA_ID)
  })

  // A container that is already exhausted when the feed loads must NOT trigger an
  // auto-expand — otherwise every reload would force sections open. StrictMode's
  // double mount makes this the case the ref guard exists to protect.
  it('does not auto-expand anything when a section is already exhausted at mount', () => {
    seedTwoSections()
    store.applyArticlePatch(`${DATE}::s1/1`, { removed: true })  // Alpha exhausted before mount

    renderFolded(ALPHA_ID, true)

    expect(expandedIds(), `already-exhausted mount must not reveal Beta, got ${JSON.stringify(expandedIds())}`)
      .not.toContain(BETA_ID)
  })
})
