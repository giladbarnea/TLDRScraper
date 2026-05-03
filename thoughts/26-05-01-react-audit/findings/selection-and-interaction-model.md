---
status: pending
last_updated: 2026-05-03 15:10, bb6b54a
---

# Selection & Interaction Model

## 1. High: `InteractionContext` broadcasts every interaction change to the whole feed

**Rule:** `rerender-memo`, `rerender-dependencies`

`client/src/contexts/InteractionContext.jsx` exposes one context value that mixes:
1. global booleans (`isSelectMode`),
2. mutable sets (`selectedIds`, `expandedContainerIds`),
3. lookup helpers (`isSelected`, `isExpanded`), and
4. action functions whose identities also depend on current state (`itemShortPress` via `dispatchWithDecision`).

That means every selection toggle, expand/collapse, or suppress-latch consumption changes the provider value and re-renders **all** consumers: `App.jsx`, every `Selectable`, every `FoldableContainer`, every `ArticleCard` path that reads `useInteraction`, and `useDigest`.

This is the dominant performance smell in this domain because the selection system sits across the entire feed. `Selectable`'s local `useMemo` does not help once the component has already been forced to re-render.

**Suggested direction:** split this into narrower subscriptions (for example: selection-mode context, expansion context, command context, or an external store with selectors) so a single item toggle only re-renders the affected item plus the tiny surfaces that actually need aggregate state.

## 2. Medium: article-action bus subscriptions churn on ordinary card re-renders

**Rule:** `advanced-use-latest`, `rerender-dependencies`

In `client/src/components/ArticleCard.jsx`, the `subscribeToArticleAction()` effect depends on `summary`:

```jsx
useEffect(() => {
  return subscribeToArticleAction(article.url, (action) => {
    ...
  })
}, [article.url, isRemoved, summary])
```

But `useSummary()` returns a fresh object each render (`client/src/hooks/useSummary.js`), so cards unsubscribe/re-subscribe frequently even when the bus wiring itself has not meaningfully changed. In practice this churn gets amplified by issue #1, because broad interaction-driven re-renders also rebuild these subscriptions across many cards.

**Suggested direction:** subscribe once per URL and read the latest summary handlers/state through stable callbacks or a `useLatest`/ref pattern.
