---
name: client/articles-and-lifecycle
description: Client article lifecycle domain and reducer pattern.
last_updated: 2026-06-09 05:17
---
# Client: Articles and Lifecycle

[→ Server: Articles & Data](../server/articles-and-data.md) | [→ State Machines: Articles & Summaries](../state-machines/articles-and-summaries.md)

## Article Lifecycle (Domain A)

Article lifecycle (`unread` → `read` → `removed`) is managed via a closed reducer pattern. Components dispatch events declaratively; the reducer returns an article patch that is applied optimistically to `articleStore` and persisted through the daily payload mutation queue. See [State Machines: Articles and Summaries](../state-machines/articles-and-summaries.md#1-article-lifecycle) for states, events, and transitions.

**Key modules:** `reducers/articleLifecycleReducer.js`, `hooks/useArticleState.js`, `store/articleStore.js`, `lib/dailyPayloadMutations.js`

---

## Sequence Diagram

> Focus: The "Reading Flow"—from clicking a card to marking it as removed.

```
TIME   ACTOR              ACTION                                TARGET
│
├───►  User               Clicks Article Card               ──► ArticleCard
│
├───►  ArticleCard        Delegates click decision          ──► interactionActions.itemShortPress(articleId)
│                         (Normal: open / Select: toggle)
│
├───►  ArticleCard        Checks TLDR availability          ──► useSummary
│      │
│      ├── (If missing)   Request TLDR Generation           ──► API (/summarize-url)
│      │   API            Returns Markdown/HTML             ──► useSummary
│      │
│      └── (If ready)     Expands Overlay                   ──► ZenModeOverlay
│
├───►  User               Reads Content (Scrolls)           ──► ZenModeOverlay
│      ZenModeOverlay     Updates Progress Bar              ──► UI (Visual)
│
├───►  User               Overscrolls Up (Pull to finish)   ──► useOverscrollUp
│
├───►  useOverscrollUp    Triggers "Complete"               ──► ArticleCard
│
├───►  ArticleCard        1. Collapses Overlay              ──► UI
│                         2. Marks as Read & Removed        ──► useArticleState
│                         3. Animates Card Exit             ──► Framer Motion
│
├───►  useArticleState    Dispatches lifecycle event        ──► articleLifecycleReducer
│                         (MARK_REMOVED)                        (Domain A)
│
├───►  useArticleState    Applies optimistic article patch   ──► articleStore
│
└───►  mutation queue     Persists state change              ──► API (/storage daily payload)
```

`useArticleState` subscribes to a single article slice by date and URL. Batch lifecycle operations build the same reducer patches, then `queueBatchArticlePatches()` groups them by date so a selection action performs one daily payload write per affected date.

---

## Per-Domain Card Styling

Cards from select domains adopt that source's color palette (text, dim, background, border) instead of the default light surface. When adding a new domain style, see `components/ArticleCard.jsx` (`SOURCE_THEMES` hostname→theme map) and `sourceThemes.css` (per-theme palette block).
