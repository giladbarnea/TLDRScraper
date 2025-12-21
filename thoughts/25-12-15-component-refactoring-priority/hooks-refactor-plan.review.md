---
last_updated: 2025-12-21 08:04, 4b3987f
---
# Hooks Refactor Plan Review

## Blindspots
- Aborted TLDR requests leave `loading` stuck `true` because the `AbortError` early return (client/src/hooks/useSummary.js:109) skips the `setLoading(false)` guard that only runs when `controller.signal.aborted` is false (client/src/hooks/useSummary.js:119). ArticleCard surfaces that spinner (`tldr.loading`) in its meta row (client/src/components/ArticleCard.jsx:229), so a cancelled fetch can pin the UI in a loading state until another request completes.
- The `state` numeric enum is unused by consumers (ArticleCard only consumes booleans: client/src/components/ArticleCard.jsx:117-173), yet the plan focuses on naming constants (client/src/hooks/useArticleState.js:14). Formalizing an unused API increases surface area; trimming `state` entirely is the simpler option.
- Several actions in `useArticleState` have no consumers (`markAsRead`, `markAsUnread`, `toggleRead`, `setRemoved`: client/src/hooks/useArticleState.js:35-58). The plan suggests consolidating, but a better outcome is to drop the dead actions rather than rename them.
- `useLocalStorage` still uses per-instance `useState` without any shared source of truth or `storage` event handling (client/src/hooks/useLocalStorage.js:3-48). If two components ever share a key (or a tab is opened twice), last-writer-wins races return; the plan only removes comments and doesn’t address this behavioral risk. FoldableContainer persists fold state through this hook (client/src/components/FoldableContainer.jsx:5-14), so clobbering remains possible if IDs collide.
- Swipe-to-remove collapses an expanded TLDR (client/src/components/ArticleCard.jsx:125-128) without marking it hidden, while other close paths mark/unmark via `markTldrHidden`/`unmarkTldrHidden` (client/src/components/ArticleCard.jsx:149-158). If `tldrHidden` is meant to reflect user intent to collapse, the removal path skips that bookkeeping.

## Disagreements / Priority tweaks
- Extracting `buttonLabel` feels low ROI because nothing consumes it today (no usages outside client/src/hooks/useSummary.js:53). I would deprioritize that in favor of fixing the loading/abort edge case.
- Given the lack of `state` consumers, exporting `ARTICLE_STATE` (or even adding it) adds noise. Prefer shrinking the API over adding constants that no one reads.

## Answers to plan questions
1) `toggleVisibility` is unused by current consumers (ArticleCard calls `toggle`, `collapse`, `expand` only: client/src/components/ArticleCard.jsx:149-173). Safe to remove; update docs that still mention it (ARCHITECTURE.md).
2) No consumer reads `state`, so exporting constants is unnecessary. Either keep the enum internal or drop `state` entirely to avoid a dormant API.
3) Action consolidation: ArticleCard only uses `toggleRemove` and the TLDR hide/show helpers (client/src/components/ArticleCard.jsx:117-158). Read-related actions have zero consumers. I would:
   - Remove `markAsRead`/`markAsUnread`/`toggleRead` and `setRemoved` unless tests rely on them.
   - Keep the TLDR helpers, or switch ArticleCard to `setTldrHidden(true/false)` if you want a single entry point without losing intent.

## Additional considerations
- When cleaning `useSummary`, also clear `abortControllerRef.current` and reset `loading` during cleanup to avoid latent states if the component unmounts mid-fetch.
- If you expect multiple foldable areas to share a key, consider a small `storage` event listener or `useSyncExternalStore` wrapper for `useLocalStorage` so state stays consistent across instances/tabs.***
