---
last_updated: 2026-04-09 14:08
---
# Client Code Dedup

Audit across persistence, hooks, overlays, feed loading, selection, and presentation found one dead component plus repeated overlay, markdown, request-token, ID, and optimistic-update logic. The follow-up refactor (81662be / PR #609) extracted `BaseOverlay`, `ZenModeOverlay`, `useFeedLoader`, `feedMerge.js`, `selectionUtils.js`, `markdownUtils.js`, `requestUtils.js`, and `zenLock.js`, then removed `ResultsDisplay.jsx`. Net effect: about 510 lines disappeared and `App.jsx`, `ArticleCard.jsx`, `useDigest.js`, and `useSupabaseStorage.js` stopped owning unrelated concerns.
