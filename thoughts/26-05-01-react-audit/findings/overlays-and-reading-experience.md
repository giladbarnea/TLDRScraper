---
status: pending
last_updated: 2026-05-02 08:02
---

# Overlays & Reading Experience

## 1. High: markdown parsing runs in hot render paths instead of being deferred/memoized

**Files:** `client/src/hooks/useSummary.js`, `client/src/hooks/useDigest.js`, `client/src/components/ElaborationPreview.jsx`, `client/src/lib/markdownUtils.js`

`markdownToHtml()` is expensive (`marked` + KaTeX + DOMPurify), but it currently runs during render:
1. `useSummary()` computes `html` for every `ArticleCard` render whenever that article already has summary markdown, even when the overlay is closed.
2. `useDigest()` computes digest HTML on every digest hook render.
3. `ElaborationPreview` reparses elaboration markdown in `AvailableBody` on render.

The worst case is the per-card summary path: selection/context updates re-render many `ArticleCard`s, and every card with cached summary markdown reparses its markdown just to keep `summary.html` warm.

**Recommendation:**
1. Defer summary HTML generation until the overlay is actually needed (`expanded` / visible path), not in the baseline hook render for every card.
2. At minimum, memoize all markdown→HTML derivations by `markdown`.
3. Keep `markdownToHtml()` out of broad fan-out render paths; pay that cost only at the reader surface.

**Best-practice tags:** `rerender-memo`, `js-cache-function-results`

## 2. Medium: `useSummary()` returns unstable commands, which makes every `ArticleCard` re-subscribe on every render

**Files:** `client/src/hooks/useSummary.js`, `client/src/components/ArticleCard.jsx`

`useSummary()` recreates `fetchSummary`, `toggle`, `collapse`, and `expand` on every render, and returns a fresh object every time. `ArticleCard` then uses the whole `summary` object as an effect dependency in the `subscribeToArticleAction()` bridge:

```jsx
useEffect(() => {
  return subscribeToArticleAction(article.url, (action) => {
    ...summary.expand()
    ...summary.fetch()
  })
}, [article.url, isRemoved, summary])
```

That means any `ArticleCard` re-render tears down and re-attaches its bus subscription, even when nothing relevant to the subscription changed. In this app, selection/context changes fan out widely, so this churn is avoidable.

**Recommendation:**
1. Make `useSummary()` command methods stable with `useCallback`.
2. Either memoize the returned API object or stop depending on the whole object in `ArticleCard`.
3. Narrow the subscription effect dependencies to the specific stable commands/status it actually needs.

**Best-practice tags:** `rerender-dependencies`, `rerender-functional-setstate`
