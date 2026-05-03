---
name: client/articles-and-lifecycle
description: Client article lifecycle domain and reducer pattern.
last_updated: 2026-05-03 15:10, bb6b54a
---
# Client: Articles and Lifecycle

[→ Server: Articles & Data](../server/articles-and-data.md) | [→ State Machines: Articles & Summaries](../state-machines/articles-and-summaries.md)

## Article Lifecycle (Domain A)

Article lifecycle (`unread` → `read` → `removed`) is managed via a closed reducer pattern. Components dispatch events declaratively; the reducer returns a storage patch applied via `useSupabaseStorage`. See [State Machines: Articles and Summaries](../state-machines/articles-and-summaries.md#1-article-lifecycle) for states, events, and transitions.

**Key modules:** `reducers/articleLifecycleReducer.js`, `hooks/useArticleState.js`

---

## Sequence Diagram

> Focus: The "Reading Flow"—from clicking a card to marking it as removed.

```
TIME   ACTOR              ACTION                                TARGET
│
├───►  User               Clicks Article Card               ──► ArticleCard
│
├───►  ArticleCard        Delegates click decision          ──► itemShortPress(articleId)
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
└───►  useArticleState    Persists State Change             ──► API (/storage)
```
